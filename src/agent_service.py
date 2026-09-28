import os
import sys
from dotenv import load_dotenv
from agent_framework import MCPStdioTool
from agent_framework.azure import AzureAISearchContextProvider
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureDeveloperCliCredential
from utils import fetch_from_wikipedia
from agent_framework.observability import configure_otel_providers

# Load environment variables from .env file
load_dotenv(override=True)

# Configure OpenTelemetry providers for tracing and logging
configure_otel_providers()

# Create a shared Azure OpenAI client instance to be used across all agents
client = FoundryChatClient(
    project_endpoint=os.environ["PROJECT_ENDPOINT"],
    model="gpt-5.4-mini",
    credential=AzureDeveloperCliCredential(),
    # api_key=os.environ["PROJECT_API_KEY"]
)

# region Tool and Context Provider Setup

# Web search tool using Azure OpenAI
web_search = client.get_web_search_tool()

# Weather forecaster agent using Azure OpenAI
weather_forecaster_agent = client.as_agent(
    name="WeatherForecaster",
    description="A meteorologist specializing in weather prediction, climate science, and atmospheric phenomena.",
    instructions=(
        "You are a professional meteorologist."
        "Use web search to find the latest weather data, forecasts, and climate research before responding."
        "Always provide citations for your sources."
    ),
    tools=[web_search]
)

# EU Compliance MCP tool using Azure OpenAI
# eu_compliance_mcp = client.get_mcp_tool(
#     name="EU Compliance MCP",
#     url="https://eu-regulations-mcp.vercel.app/mcp",
#     approval_mode="never_require",
# )

# # Eurostat MCP tool using stdio transport
# eurostat_mcp = MCPStdioTool(
#     name="Eurostat MCP",
#     command=sys.executable,
#     args=["eurostat_mcp_server.py"],
#     description="Eurostat MCP server for querying European statistics data",
# )

# # Create search provider with semantic mode (default)
# economy_context = AzureAISearchContextProvider(
#     endpoint=os.environ["SEARCH_ENDPOINT"],
#     index_name="rag-arxiv",
#     credential=AzureDeveloperCliCredential(),
#     api_key=os.environ["SEARCH_API_KEY"],
#     mode="semantic",  # Default mode
#     top_k=3,  # Number of documents to retrieve
# )

# endregion

# Define the panelists with their unique perspectives and instructions
software_engineer_agent = client.as_agent(
    name="SoftwareEngineer",
    description="A senior software engineer with deep expertise in system design, coding, and technology.",
    instructions=(
        "You are a senior software engineer with deep expertise in system design, coding, and technology."
    ),
    # tools=[web_search],

)

economist_agent = client.as_agent(
    name="Economist",
    description="An economist specializing in macroeconomics, public policy, and market dynamics.",
    instructions=(
        "You are a seasoned economist with expertise in macroeconomics, public policy, and market dynamics."
    ),
    # context_providers=[economy_context]
)

lawyer_agent = client.as_agent(
    name="Lawyer",
    description="A legal expert specializing in constitutional law, regulation, and policy.",
    instructions=(
        "You are an experienced attorney with expertise in constitutional law, regulatory frameworks, intellectual property, privacy law, and international legal standards."
    )
)

researcher_agent = client.as_agent(
    name="Researcher",
    description="An academic researcher focused on evidence-based analysis and scientific methodology.",
    instructions=(
        "You are an academic researcher with a focus on evidence-based analysis and scientific methodology."
    ),
    # tools=[fetch_from_wikipedia]
)

news_reporter_agent = client.as_agent(
    name="NewsReporter",
    description="A veteran journalist focused on factual reporting, public impact, and media ethics.",
    instructions=(
        "You are a veteran journalist with a focus on factual reporting, public impact, and media ethics."
    )
)

politician_agent = client.as_agent(
    name="Politician",
    description="A pragmatic elected official focused on governance, public opinion, and policy implementation.",
    instructions=(
        "You are a seasoned elected official with extensive experience in legislative processes, public administration, coalition building, and constituent relations."
    ))

medical_doctor_agent = client.as_agent(
    name="MedicalDoctor",
    instructions=(
        "You are an experienced physician and public health expert with clinical practice and research experience."
    ),
)


PANELISTS = [
    software_engineer_agent,
    economist_agent,    
    politician_agent,
    medical_doctor_agent,
]
