"""A2A sample: one agent exposes an A2A agent card, another discovers it and calls it.

- JokeTeller (remote): hosted over A2A with an agent card at /.well-known/agent-card.json
- Host (caller): resolves the card, wraps the remote agent with A2AAgent and uses it as a tool

Both agents use gpt-5.4-mini on Microsoft Foundry. The server and the caller run in the same
process for convenience; the caller only talks to the remote agent over HTTP via A2A.

Requirements: pip install --pre agent-framework-a2a "a2a-sdk[http-server]" uvicorn
Run:          python a2a_sample.py
"""

import asyncio
import os

import httpx
import uvicorn
from a2a.client import A2ACardResolver
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from agent_framework.a2a import A2AAgent, A2AExecutor
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureDeveloperCliCredential
from dotenv import load_dotenv
from starlette.applications import Starlette

load_dotenv(override=True)

HOST, PORT = "localhost", 9999
BASE_URL = f"http://{HOST}:{PORT}"

client = FoundryChatClient(
    project_endpoint=os.environ["PROJECT_ENDPOINT"],
    model="gpt-5.4-mini",
    credential=AzureDeveloperCliCredential(),
)


# region Remote agent exposed over A2A

joke_agent = client.as_agent(
    name="JokeTeller",
    description="Tells short, family-friendly jokes about any topic.",
    instructions="You are a comedian. Reply with one short, family-friendly joke about the requested topic.",
)

joke_agent_card = AgentCard(
    name="JokeTeller",
    description="Tells short, family-friendly jokes about any topic.",
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[AgentInterface(url=f"{BASE_URL}/", protocol_binding="JSONRPC")],
    skills=[
        AgentSkill(
            id="tell_joke",
            name="Tell a joke",
            description="Tells a short joke about a given topic.",
            tags=["humor", "jokes"],
            examples=["Tell me a joke about cats."],
        )
    ],
)


def build_a2a_app() -> Starlette:
    request_handler = DefaultRequestHandler(
        agent_executor=A2AExecutor(joke_agent, stream=True),
        task_store=InMemoryTaskStore(),
        agent_card=joke_agent_card,
    )
    return Starlette(
        routes=[
            *create_agent_card_routes(joke_agent_card),  # GET /.well-known/agent-card.json
            *create_jsonrpc_routes(request_handler, "/"),
        ]
    )

# endregion


# region Caller agent that discovers and calls the remote agent


async def run_caller() -> None:
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        resolver = A2ACardResolver(httpx_client=http_client, base_url=BASE_URL)
        card = await resolver.get_agent_card()
    print(f"Discovered A2A agent: {card.name} - {card.description}")

    async with A2AAgent(agent_card=card) as remote_joke_agent:
        host_agent = client.as_agent(
            name="Host",
            instructions=(
                "You are a friendly party host. When the user asks for a joke, "
                "call the JokeTeller tool and share its joke with a one-line intro."
            ),
            tools=[remote_joke_agent.as_tool()],
        )

        question = "Can you tell me a joke about programmers?"
        print(f"\nUser: {question}")
        response = await host_agent.run(question)
        print(f"Host: {response.text}")

# endregion


async def main() -> None:
    server = uvicorn.Server(uvicorn.Config(build_a2a_app(), host=HOST, port=PORT, log_level="warning"))
    server_task = asyncio.create_task(server.serve())
    while not server.started:
        if server_task.done():
            raise RuntimeError(f"A2A server failed to start on {BASE_URL}")
        await asyncio.sleep(0.1)
    print(f"JokeTeller A2A agent card: {BASE_URL}/.well-known/agent-card.json")

    try:
        await run_caller()
        await asyncio.sleep(100)
    finally:
        server.should_exit = True
        await server_task


if __name__ == "__main__":
    asyncio.run(main())
