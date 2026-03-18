from agent_framework import AgentExecutorResponse
from agent_framework.orchestrations import ConcurrentBuilder, GroupChatBuilder, GroupChatState
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


# This workflow runs all panelists in parallel and aggregates their responses into a single output.
parallel_workflow = (
    ConcurrentBuilder(participants=PANELISTS)
    .with_aggregator(_aggregate)
    .build()
)

# This workflow runs the panelists in a round-robin fashion for a specified number of rounds.


def round_robin_selector(state: GroupChatState) -> str:
    """A round-robin selector function that picks the next speaker based on the current round index."""

    participant_names = list(state.participants.keys())
    return participant_names[state.current_round % len(participant_names)]


group_chat_workflow = (
    GroupChatBuilder(
        participants=PANELISTS,
        selection_func=round_robin_selector)
    .with_max_rounds(7)
    .build()
)

if __name__ == "__main__":
    serve(entities=[parallel_workflow, group_chat_workflow], auto_open=True)
