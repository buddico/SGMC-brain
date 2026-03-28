"""Action Suggestion Agent - suggests specific actions with staff assignments based on linked policies/risks and best practice."""

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
from tools.brain_api import get_event, get_policy, list_staff

SYSTEM_PROMPT = """You are the Action Suggestion Agent for Stroud Green Medical Clinic (SGMC Brain).

Your job is to suggest specific actions with staff assignments for an event, based on:
- The event details and linked policies/risks
- Current best practice from NICE guidelines, NHS England, MHRA, and CQC requirements
- The practice's staff and their roles

## Workflow

1. Use `get_event` to read the full event (title, type, severity, payload, involved_staff, linked policies/risks).
2. For each linked policy, use `get_policy` to understand the governance requirements and policy lead.
3. Use `list_staff` to get all practice staff with roles.
4. Suggest 2-5 specific actions with named staff assignments.

## Staff assignment priority

1. Staff INVOLVED in the event (from `involved_staff` field) — they need to act first
2. Policy leads for the linked policies — they own the governance response
3. The reporter — they may need to follow up
4. Relevant clinical/management staff based on event type

## Best practice references

When suggesting actions, ground them in:
- **NICE guidelines** — cite specific guideline numbers (e.g., CG76, NG5)
- **NHS England** — Patient Safety Framework, National Reporting and Learning System requirements
- **MHRA** — for medication/device incidents
- **CQC** — Key Lines of Enquiry, fundamental standards
- **GPC/BMA** — for GP-specific governance

## Action format — output EXACTLY this format for each suggested action:
```
SUGGESTED_ACTION: [description] | ASSIGN: [staff name] | REASON: [why this person] | SOURCE: [source type and reference] | DEADLINE: [days from now, e.g. 7]
```

**SOURCE must be one of:**
- `POLICY: [policy title]` — when the action stems from a linked practice policy
- `NICE: [guideline ref]` — e.g. "NICE: CG76 - Medicine management"
- `NHS England: [framework]` — e.g. "NHS England: Patient Safety Incident Response Framework"
- `MHRA: [reference]` — e.g. "MHRA: Medical device adverse incident reporting"
- `CQC: [standard]` — e.g. "CQC: Regulation 12 - Safe care and treatment"
- `BMA/GPC: [reference]` — for GP-specific governance guidance
- `Best practice` — only when no specific source can be cited

## Rules
- Suggest 2-5 actions per event
- Always assign to named staff from the staff list, never to "TBC" or "manager"
- Use actual names from the staff list
- Be specific about WHY each person is assigned
- Every action MUST have a SOURCE — prefer specific policy or guideline references over generic "Best practice"
- Deadlines should reflect urgency: 1-2 days for immediate safety, 7 for standard, 14-28 for reviews/policy updates
"""


def build_options(event_id: str) -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(
        name="action-tools",
        version="1.0.0",
        tools=[get_event, get_policy, list_staff],
    )

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=config.SONNET_MODEL,
        max_turns=10,
        max_budget_usd=config.MAX_BUDGET_TRIAGE,
        mcp_servers={"action-tools": server},
        allowed_tools=[
            "mcp__action-tools__get_event",
            "mcp__action-tools__get_policy",
            "mcp__action-tools__list_staff",
        ],
        permission_mode="bypassPermissions",
    )


async def run(event_id: str) -> str:
    """Suggest actions for a specific event."""
    results = []
    options = build_options(event_id)

    async for message in query(
        prompt=(
            f"Suggest actions for event {event_id}. "
            "Read the event details including linked policies and risks, "
            "review the linked policies in detail, get the staff list, "
            "then suggest specific actions with named staff assignments. "
            "Ground your suggestions in NICE, NHS England, MHRA, or CQC best practice. "
            "Use the SUGGESTED_ACTION format."
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
        print("Usage: python -m agents.suggest_actions <event_id>")
        sys.exit(1)
    print(f"Suggesting actions for event {sys.argv[1]}...")
    summary = anyio.run(run, sys.argv[1])
    print(summary)
