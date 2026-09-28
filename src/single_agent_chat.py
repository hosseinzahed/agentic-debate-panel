from agent_framework.devui import serve

from agent_service import weather_forecaster_agent

if __name__ == "__main__":
    serve(entities=[weather_forecaster_agent], auto_open=True)
