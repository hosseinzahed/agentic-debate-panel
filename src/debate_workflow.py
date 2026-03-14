from agent_framework import AgentExecutorResponse
from agent_framework.orchestrations import ConcurrentBuilder
from agent_framework.devui import serve

from agent_service import PANELISTS


def _aggregate(results: list[AgentExecutorResponse]) -> str:
    sections = []
    for result in results:
        last_msg = result.agent_response.messages[-1] if result.agent_response.messages else None
        if not last_msg:
            continue
        name = last_msg.author_name or "Panelist"
        sections.append(f"## {name}\n\n{last_msg.text}")
    return "\n\n---\n\n".join(sections)


workflow = (
    ConcurrentBuilder(participants=PANELISTS)
    .with_aggregator(_aggregate)
    .build()
)


if __name__ == "__main__":
    serve(entities=[workflow], auto_open=True)
