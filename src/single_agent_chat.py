from agent_framework.devui import serve

from agent_service import PANELISTS

if __name__ == "__main__":
    serve(entities=PANELISTS, auto_open=True)
