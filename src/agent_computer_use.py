import os
from dotenv import load_dotenv
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential, AzureDeveloperCliCredential
from agent_framework.observability import configure_otel_providers
from agent_framework.devui import serve

# Load environment variables from .env file
load_dotenv(override=True)

# Configure OpenTelemetry providers for tracing and logging
configure_otel_providers()


def main() -> None:

    # Create a shared Azure OpenAI client instance to be used across all agents
    client = FoundryChatClient(
        project_endpoint=os.environ["PROJECT_ENDPOINT"],
        model="computer-use-preview",
        credential=AzureDeveloperCliCredential(),
        # api_key=os.environ["PROJECT_API_KEY"]
    )

    # Get a computer use tool instance for the agent to interact with a Windows environment
    computer_use_tool = client.get_computer_use_tool(
        environment="windows",
        display_width=1200,
        display_height=800
    )

    agent = Agent(
        name="Computer Automation Agent",
        client=client,
        instructions=(
            "You are a computer automation assistant. Be direct and efficient. "
            "When you reach the search results page, describe the actual result titles you can see."
        ),
        tools=[computer_use_tool],
        # computer-use-preview requires truncation="auto" (Responses API defaults to "disabled")
        default_options={"truncation": "auto"},
    )

    # Serve the agent using the DevUI interface
    serve(entities=[agent], auto_open=True, auth_enabled=False)


if __name__ == "__main__":
    main()
