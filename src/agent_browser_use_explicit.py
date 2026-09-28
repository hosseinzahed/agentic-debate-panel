import asyncio
import json
import os
from typing import Annotated

from dotenv import load_dotenv
from agent_framework import Agent, FunctionTool, tool
from agent_framework.foundry import FoundryChatClient, FoundryToolbox
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    BrowserAutomationPreviewToolboxTool,
    BrowserAutomationToolConnectionParameters,
    BrowserAutomationToolParameters,
)
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import AzureDeveloperCliCredential
from agent_framework.observability import configure_otel_providers
from agent_framework.devui import serve
from playwright.async_api import Browser, Page, Playwright, async_playwright
from pydantic import Field


# Load environment variables from .env file
load_dotenv(override=True)

# Configure OpenTelemetry providers for tracing and logging
configure_otel_providers()

TOOLBOX_NAME = "browser-automation-toolbox"
PAGE_CHUNK_CHARS = 12000
MAX_LINKS = 60


def get_or_create_browser_toolbox(project: AIProjectClient, connection_id: str) -> str:
    """Return the MCP endpoint of a toolbox containing the Browser Automation tool.

    Reuses the toolbox's default version when it already points at ``connection_id``;
    otherwise publishes a new version (toolbox versions are immutable).
    See https://learn.microsoft.com/azure/foundry/agents/how-to/tools/browser-automation
    """
    version = None
    try:
        toolbox = project.toolboxes.get(TOOLBOX_NAME)
        current = project.toolboxes.get_version(TOOLBOX_NAME, toolbox.default_version).as_dict()
        connections = [
            t.get("browser_automation_preview", {}).get("connection", {}).get("project_connection_id")
            for t in current.get("tools", [])
        ]
        if connection_id in connections:
            version = toolbox.default_version
    except ResourceNotFoundError:
        toolbox = None

    if version is None:
        created = project.toolboxes.create_version(
            name=TOOLBOX_NAME,
            description="Toolbox with the Browser Automation tool",
            tools=[
                BrowserAutomationPreviewToolboxTool(
                    browser_automation_preview=BrowserAutomationToolParameters(
                        connection=BrowserAutomationToolConnectionParameters(
                            project_connection_id=connection_id,
                        )
                    )
                )
            ],
        )
        version = created.version
        if toolbox is not None:
            project.toolboxes.update(TOOLBOX_NAME, default_version=version)

    endpoint = os.environ["PROJECT_ENDPOINT"].rstrip("/")
    return f"{endpoint}/toolboxes/{TOOLBOX_NAME}/versions/{version}/mcp?api-version=v1"


class RemoteBrowser:
    """Drives a remote Chromium provisioned by the Browser Automation toolbox.

    The toolbox's only MCP tool (``create_session``) provisions a browser in the Playwright
    workspace and returns a CDP URL; it doesn't navigate by itself. This class connects to
    that browser with Playwright and exposes navigation/reading as agent function tools.
    """

    def __init__(self, credential: AzureDeveloperCliCredential, toolbox_mcp_url: str) -> None:
        self._credential = credential
        self._toolbox_mcp_url = toolbox_mcp_url
        self._lock = asyncio.Lock()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None
        self._page_text = ""

    async def _create_session_cdp_url(self) -> str:
        async with FoundryToolbox(self._credential, url=self._toolbox_mcp_url, timeout=300.0) as toolbox:
            create_session = next(f for f in toolbox.functions if f.name.endswith("create_session"))
            result = await create_session.invoke()
        return json.loads(result[0].text)["cdp_url"]

    async def _get_page(self) -> Page:
        if self._page and self._browser and self._browser.is_connected() and not self._page.is_closed():
            return self._page
        await self.close()
        cdp_url = await self._create_session_cdp_url()
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url, timeout=120_000)
        context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
        self._page = context.pages[0] if context.pages else await context.new_page()
        self._page.set_default_timeout(30_000)
        return self._page

    async def close(self) -> None:
        for closer in (self._browser and self._browser.close, self._playwright and self._playwright.stop):
            if closer:
                try:
                    await closer()
                except Exception:
                    pass
        self._playwright = self._browser = self._page = None

    async def _snapshot(self, page: Page) -> str:
        try:
            await page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
        self._page_text = await page.inner_text("body")
        links = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => [e.innerText.trim(), e.href]).filter(([t]) => t)",
        )
        link_lines = "\n".join(f"- {text[:80]} -> {href}" for text, href in links[:MAX_LINKS])
        return (
            f"URL: {page.url}\nTitle: {await page.title()}\n\n"
            f"{self._chunk(1)}\n\nLinks (first {MAX_LINKS}):\n{link_lines}"
        )

    def _chunk(self, part: int) -> str:
        total = max(1, -(-len(self._page_text) // PAGE_CHUNK_CHARS))
        start = (part - 1) * PAGE_CHUNK_CHARS
        return f"Page text (part {part}/{total}):\n{self._page_text[start:start + PAGE_CHUNK_CHARS]}"

    async def _run(self, action) -> str:
        async with self._lock:
            try:
                page = await self._get_page()
                return await action(page)
            except Exception as ex:
                if self._browser is None or not self._browser.is_connected():
                    await self.close()
                return f"Browser error: {type(ex).__name__}: {ex}"

    def tools(self) -> list[FunctionTool]:
        @tool
        async def open_url(url: Annotated[str, Field(description="Absolute URL to open.")]) -> str:
            """Open a URL in the remote browser and return the page title, visible text and links."""

            async def action(page: Page) -> str:
                await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                return await self._snapshot(page)

            return await self._run(action)

        @tool
        async def click(
            text: Annotated[str, Field(description="Visible text of the link or button to click.")],
        ) -> str:
            """Click a link or button by its visible text, then return the resulting page."""

            async def action(page: Page) -> str:
                target = (
                    page.get_by_role("link", name=text)
                    .or_(page.get_by_role("button", name=text))
                    .or_(page.get_by_text(text))
                    .first
                )
                await target.click()
                return await self._snapshot(page)

            return await self._run(action)

        @tool
        async def fill(
            field: Annotated[str, Field(description="Label or placeholder of the input field.")],
            value: Annotated[str, Field(description="Text to type into the field.")],
            submit: Annotated[bool, Field(description="Press Enter after typing.")] = False,
        ) -> str:
            """Type into an input field (found by label or placeholder), optionally submitting it."""

            async def action(page: Page) -> str:
                target = page.get_by_label(field).or_(page.get_by_placeholder(field)).first
                await target.fill(value)
                if submit:
                    await target.press("Enter")
                return await self._snapshot(page)

            return await self._run(action)

        @tool
        async def read_more(
            part: Annotated[int, Field(description="1-based part number of the current page text.")],
        ) -> str:
            """Return another part of the current page's text when it's too long for one response."""

            async def action(page: Page) -> str:
                return self._chunk(part)

            return await self._run(action)

        return [open_url, click, fill, read_more]


def main() -> None:
    credential = AzureDeveloperCliCredential()

    # BROWSER_CONNECTION_ID must be the Foundry project connection resource ID
    # (/subscriptions/.../projects/<project>/connections/<name>), not the Playwright wss:// URL.
    project = AIProjectClient(endpoint=os.environ["PROJECT_ENDPOINT"], credential=credential)
    toolbox_mcp_url = get_or_create_browser_toolbox(project, os.environ["BROWSER_CONNECTION_ID"])
    browser = RemoteBrowser(credential, toolbox_mcp_url)

    client = FoundryChatClient(
        project_endpoint=os.environ["PROJECT_ENDPOINT"],
        model="gpt-5.6-sol",
        credential=credential,
    )

    agent = Agent(
        name="Browser Automation Agent",
        client=client,
        instructions=(
            "You are a browser automation assistant. Be direct and efficient. "
            "Use the browser tools to open the URLs the user shares, click through pages and "
            "use read_more when the page text is split into parts. Base your answer only on "
            "what the tools return; if a tool fails, say so instead of answering from memory."
        ),
        tools=browser.tools(),
    )

    # Serve the agent using the DevUI interface
    serve(entities=[agent], auto_open=True, auth_enabled=False)


if __name__ == "__main__":
    main()
