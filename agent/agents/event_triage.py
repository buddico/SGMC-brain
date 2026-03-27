"""Event Triage Agent - suggests policy links, risk connections, AND specific actions with staff assignments."""

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
from tools.brain_api import get_event, list_policies, list_risks, list_staff, update_event_links

SYSTEM_PROMPT = """You are the Event Triage Agent for Stroud Green Medical Clinic (SGMC Brain).

When a new event is reported, you:
1. Identify relevant policies and link them
2. Identify relevant risks
3. Suggest specific actions with staff assignments based on policy leads and involvement

## Workflow

1. Use `get_event` to read the full event (title, type, severity, payload, involved_staff).
2. Use `list_policies` to get all active policies (each has a policy_lead_name).
3. Use `list_risks` to get current risks.
4. Use `list_staff` to get all practice staff with roles.
5. Use `update_event_links` to link relevant policies and risks.
6. Output a structured triage result.

## Action Suggestions

For each linked policy, suggest concrete actions based on the event. Assign staff intelligently:

**Priority order for action assignment:**
1. Staff INVOLVED in the event (from `involved_staff` field) — they need to act first
2. Policy leads for the linked policies — they own the governance response
3. The reporter — they may need to follow up
4. Relevant clinical/management staff based on event type

**Action format — output EXACTLY this format for each suggested action:**
```
SUGGESTED_ACTION: [description] | ASSIGN: [staff name] | REASON: [why this person] | DEADLINE: [days from now, e.g. 7]
```

## Example

For a fridge temperature breach:
- Link: Infection Prevention and Control Policy (lead: Kaydeen Johnson)
- Link: Medical Equipment and Cold Chain Policy
- SUGGESTED_ACTION: Quarantine all vaccines in affected fridge and check temperatures | ASSIGN: Kaydeen Johnson | REASON: IPC Lead and named in event | DEADLINE: 1
- SUGGESTED_ACTION: Contact PHE about affected vaccine batches | ASSIGN: Dr Anjan Chakraborty | REASON: Prescribing Lead, clinical decision required | DEADLINE: 3
- SUGGESTED_ACTION: Review cold chain monitoring procedures | ASSIGN: Amy Cox | REASON: Practice Manager, equipment procurement | DEADLINE: 14

## Rules
- Link 1-3 policies, 0-2 risks per event
- Suggest 2-5 actions per event
- Always assign to named staff, never to "TBC" or "manager"
- Use actual names from the staff list
- Be specific about WHY each person is assigned
- If event suggests a new risk, note it as: NEW_RISK: [description]
"""


def build_options() -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(
        name="triage-tools",
        version="1.0.0",
        tools=[get_event, list_policies, list_risks, list_staff, update_event_links],
    )

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=config.SONNET_MODEL,
        max_turns=10,
        max_budget_usd=config.MAX_BUDGET_TRIAGE,
        mcp_servers={"triage-tools": server},
        allowed_tools=[
            "mcp__triage-tools__get_event",
            "mcp__triage-tools__list_policies",
            "mcp__triage-tools__list_risks",
            "mcp__triage-tools__list_staff",
            "mcp__triage-tools__update_event_links",
        ],
        permission_mode="bypassPermissions",
    )


async def run(event_id: str) -> str:
    """Triage a specific event. Returns the agent's analysis with action suggestions."""
    results = []
    options = build_options()

    async for message in query(
        prompt=(
            f"Triage event {event_id}. Read the event details (including involved_staff), "
            "find relevant policies and risks, link them, then suggest specific actions "
            "with named staff assignments. Use the SUGGESTED_ACTION format."
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
