import asyncio
import json
import os

from dotenv import load_dotenv
from agent_framework import Agent, MCPStdioTool
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


# Load environment variables from .env file
load_dotenv(override=True)

# Configure OpenTelemetry providers for tracing and logging
configure_otel_providers()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"].rstrip("/")
TOOLBOX_NAME = "browser-automation-toolbox"
credential = AzureDeveloperCliCredential()


def get_toolbox_url() -> str:
    """Get (or create) the Browser Automation toolbox and return its MCP endpoint.
    See https://learn.microsoft.com/azure/foundry/agents/how-to/tools/browser-automation
    """
    project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
    try:
        version = project.toolboxes.get(TOOLBOX_NAME).default_version
    except ResourceNotFoundError:
        version = project.toolboxes.create_version(
            name=TOOLBOX_NAME,
            description="Toolbox with the Browser Automation tool",
            tools=[
                BrowserAutomationPreviewToolboxTool(
                    browser_automation_preview=BrowserAutomationToolParameters(
                        connection=BrowserAutomationToolConnectionParameters(
                            project_connection_id=os.environ["BROWSER_CONNECTION_ID"],
                        )
                    )
                )
            ],
        ).version
    return f"{PROJECT_ENDPOINT}/toolboxes/{TOOLBOX_NAME}/versions/{version}/mcp?api-version=v1"


async def create_browser_session() -> str:
    """Provision a remote browser in the Playwright workspace and return its CDP URL."""
    async with FoundryToolbox(credential, url=get_toolbox_url()) as toolbox:
        session = await toolbox.functions[0].invoke()
    return json.loads(session[0].text)["cdp_url"]


def main() -> None:
    # Playwright MCP drives the remote browser and provides the browser tools (navigate, click, type, snapshot, ...).
    # The CDP URL contains an access token, so pass it via env instead of the command line.
    playwright_mcp = MCPStdioTool(
        name="playwright",
        command="npx",
        args=["-y", "@playwright/mcp@latest"],
        env={"PLAYWRIGHT_MCP_CDP_ENDPOINT": asyncio.run(create_browser_session())},
        # Exclude code-execution/file tools so web content can't make the agent run arbitrary code
        allowed_tools=[
            "browser_navigate", "browser_navigate_back", "browser_snapshot", "browser_click",
            "browser_type", "browser_fill_form", "browser_select_option", "browser_press_key",
            "browser_hover", "browser_wait_for", "browser_tabs", "browser_take_screenshot",
        ],
    )

    client = FoundryChatClient(
        project_endpoint=PROJECT_ENDPOINT,
        model="gpt-5.6-sol",
        credential=credential,
    )

    agent = Agent(
        name="Browser Automation Agent",
        client=client,
        instructions=(
            "You are a browser automation assistant. Be direct and efficient. "
            "Use the browser tools to open the URLs the user shares and base your answer "
            "only on what they return. If a tool fails, say so instead of answering from memory."
        ),
        tools=[playwright_mcp],
    )

    # Serve the agent using the DevUI interface
    serve(entities=[agent], auto_open=True, auth_enabled=False)


if __name__ == "__main__":
    main()
