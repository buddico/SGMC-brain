"""Event Triage Agent - links relevant policies and risks to an event. Nothing more."""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    create_sdk_mcp_server,
    query,
)

from config import config
from tools.brain_api import get_event, list_policies, list_risks, update_event_links

SYSTEM_PROMPT = """You are the Event Triage Agent for Stroud Green Medical Clinic (SGMC Brain).

Your ONLY job is to identify and link relevant policies and risks to an event. You do NOT suggest actions or investigations.

## Workflow

1. Use `get_event` to read the full event (title, type, severity, payload, involved_staff).
2. Use `list_policies` to get all active policies (each has a policy_lead_name).
3. Use `list_risks` to get current risks.
4. Use `update_event_links` to link relevant policies and risks to the event.
5. Output a brief summary of what you linked and why.

## Rules
- Link 1-3 policies that are most relevant to the event
- Link 0-2 risks that are directly related
- Explain briefly why each policy/risk was linked
- Do NOT suggest actions, investigations, or staff assignments
- If the event suggests a new risk that doesn't exist yet, note it as: NEW_RISK: [description]

## Output format

For each link, output:
LINKED_POLICY: [policy title] | REASON: [why it's relevant]
LINKED_RISK: [risk title] | REASON: [why it's relevant]
"""


def build_options() -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(
        name="triage-tools",
        version="1.0.0",
        tools=[get_event, list_policies, list_risks, update_event_links],
    )

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=config.SONNET_MODEL,
        max_turns=8,
        max_budget_usd=config.MAX_BUDGET_TRIAGE,
        mcp_servers={"triage-tools": server},
        allowed_tools=[
            "mcp__triage-tools__get_event",
            "mcp__triage-tools__list_policies",
            "mcp__triage-tools__list_risks",
            "mcp__triage-tools__update_event_links",
        ],
        permission_mode="bypassPermissions",
    )


async def run(event_id: str) -> str:
    """Triage a specific event. Links policies and risks only."""
    results = []
    options = build_options()

    async for message in query(
        prompt=(
            f"Triage event {event_id}. Read the event details, "
            "find relevant policies and risks, and link them. "
            "Output LINKED_POLICY and LINKED_RISK lines explaining each link."
        ),
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    results.append(block.text)
        elif isinstance(message, ResultMessage):
            results.append(f"[Cost: ${message.total_cost_usd:.4f}]")

    return "\n".join(results)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m agents.event_triage <event_id>")
        sys.exit(1)
    print(f"Triaging event {sys.argv[1]}...")
    summary = anyio.run(run, sys.argv[1])
    print(summary)
