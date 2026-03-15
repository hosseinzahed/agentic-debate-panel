# 🎙️ Agentic Debate Panel

An agentic debate panel powered by **Microsoft Agent Framework** and **Azure AI**. Throw any topic at the panel and watch seven distinct expert agents argue it from their own unique perspectives — simultaneously.

---

## 🧠 About the Project

The Agentic Debate Panel simulates a multi-perspective expert panel discussion. A user submits a debate topic and each panelist agent independently analyses the topic from their professional standpoint and responds concurrently. The responses are then aggregated into a single structured summary.

The panel consists of seven expert agents:

| Agent | Perspective |
|---|---|
| 👩‍💻 **Software Engineer** | Technical feasibility, system design, engineering trade-offs |
| 📊 **Economist** | Market dynamics, incentives, cost-benefit analysis |
| ⚖️ **Lawyer** | Legal precedent, regulation, EU compliance |
| 🔬 **Researcher** | Academic evidence, scientific literature, Eurostat data |
| 📰 **News Reporter** | Current events, journalistic framing, real-world context |
| 🏛️ **Politician** | Political feasibility, public sentiment, governance |
| 🩺 **Medical Doctor** | Health outcomes, clinical evidence, bioethics |

Each agent is limited to 100 words per response to keep the debate sharp and readable.

### 🤖 Run Modes

- **Debate Workflow** (`debate_workflow.py`) — Runs all agents concurrently via a `ConcurrentBuilder` orchestration and aggregates their responses into a single output. Served via the Agent Framework Dev UI.
- **Single Agent Chat** (`single_agent_chat.py`) — Launches each panelist individually for direct chat. Useful for exploring a single agent's behaviour.

---

## 🏗️ Agent Framework

This project uses the **[Microsoft Agent Framework](https://pypi.org/project/agent-framework/)** — a Python library for building structured, observable, and composable AI agent workflows on top of Azure AI.

Key features used in this project:

- **`client.as_agent()`** — Wraps an Azure OpenAI model deployment as a named agent with custom instructions.
- **`ConcurrentBuilder`** — Orchestration primitive that runs multiple agents in parallel and merges results via a custom aggregator function.
- **`AzureOpenAIResponsesClient`** — Manages the connection to your Azure AI Foundry project endpoint.
- **`AzureAISearchContextProvider`** — Injects relevant documents from Azure AI Search into agent context (RAG).
- **`MCPStdioTool`** — Connects agents to local MCP servers over stdio (used for the Eurostat data server).
- **`client.get_mcp_tool()`** — Connects agents to remote MCP servers over HTTP (used for EU regulations).
- **`client.get_web_search_tool()`** — Gives agents access to Bing web search via Azure AI.
- **`configure_otel_providers()`** — Sets up OpenTelemetry tracing and logging for full observability.
- **Dev UI (`agent_framework.devui.serve`)** — Launches a local browser-based UI to interact with agents and workflows.

---

## ☁️ Azure Resources Required

You need the following Azure resources before running the project:

### 1. 🤖 Azure AI Foundry Project
An **Azure AI Foundry** project (backed by an Azure AI Hub) that provides:
- A deployed chat model (e.g. `gpt-4o-mini` or `gpt-4o`)
- Web search tool capability (Bing grounding)

Once created, copy the **project endpoint** from the Azure AI Foundry portal.

### 2. 🔍 Azure AI Search
An **Azure AI Search** instance with a semantic search index named `rag-arxiv` containing economic/research papers or any documents you want the Economist and Researcher agents to retrieve context from.

You need the **search endpoint** and an **API key** with read access.

---

## ⚙️ Setup & Configuration

### 1. Clone the repository

```bash
git clone https://github.com/hosseinzahed/agentic-debate-panel.git
cd agentic-debate-panel
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r src/requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the `src/` directory with the following values:

```env
# Azure AI Foundry project endpoint
PROJECT_ENDPOINT=https://<your-hub>.services.ai.azure.com/api/projects/<your-project>

# Azure AI Search
SEARCH_ENDPOINT=https://<your-search-service>.search.windows.net
SEARCH_API_KEY=<your-search-api-key>
```

> **Authentication:** The project uses `AzureCliCredential` for authenticating to Azure AI Foundry. Make sure you are logged in via `az login` before running.

---

## 🚀 Running the Project

Make sure you are inside the `src/` directory before running:

```bash
cd src
```

### Run the full debate panel (concurrent workflow)

```bash
python debate_workflow.py
```

This launches the Agent Framework Dev UI in your browser. Enter a debate topic and all seven panelists will respond concurrently.

### Run individual agents (single agent chat)

```bash
python single_agent_chat.py
```

This opens the Dev UI with each panelist available for direct one-on-one conversation.

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `agent-framework` | Core agent orchestration and Azure AI integration |
| `agent-framework-devui` | Local browser UI for interacting with agents |
| `azure-identity` | Azure credential management (`AzureCliCredential`) |
| `python-dotenv` | Load environment variables from `.env` |
| `mcp` | Model Context Protocol client/server support |
| `markitdown` | Convert HTML/PDF assets to Markdown for agent context |
| `httpx` | HTTP client used by MCP tools |
| `pydantic` | Data validation |

