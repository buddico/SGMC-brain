"""Investigation Suggestion Agent - suggests investigation notes based on linked policies/risks and best practice."""

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

SYSTEM_PROMPT = """You are the Investigation Suggestion Agent for Stroud Green Medical Clinic (SGMC Brain).

Your job is to suggest investigation notes for an event based on:
- The event details and linked policies/risks
- Current best practice from NICE guidelines, NHS England, MHRA, and CQC requirements
- Root cause analysis methodology

## Workflow

1. Use `get_event` to read the full event (title, type, severity, payload, involved_staff, linked policies/risks).
2. For each linked policy, use `get_policy` to understand the relevant governance context.
3. Use `list_staff` to understand who was involved.
4. Suggest a structured investigation approach.

## Output format

Output the investigation suggestion as structured text that can be pasted into the investigation notes field. Include:

1. **Immediate findings** — what is known from the event report
2. **Root cause analysis** — contributing factors to investigate (use the "5 Whys" or fishbone approach as appropriate)
3. **Evidence to gather** — documents, statements, records to review
4. **Best practice reference** — cite relevant NICE guidelines, NHS England frameworks, MHRA guidance, or CQC key lines of enquiry (KLOEs) that apply
5. **Staff to interview** — based on involvement and policy leads

## Rules
- Be specific to the event type and details, not generic
- Reference actual policy names that are linked to the event
- Cite specific NICE/NHS England/MHRA guidance where relevant (e.g., "NICE CG76", "NHS England Patient Safety Framework")
- Keep the suggestion concise but thorough — suitable for a GP practice investigation
- Do NOT suggest actions — that's a separate function
"""


def build_options(event_id: str) -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(
        name="investigation-tools",
        version="1.0.0",
        tools=[get_event, get_policy, list_staff],
    )

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=config.SONNET_MODEL,
        max_turns=10,
        max_budget_usd=config.MAX_BUDGET_TRIAGE,
        mcp_servers={"investigation-tools": server},
        allowed_tools=[
            "mcp__investigation-tools__get_event",
            "mcp__investigation-tools__get_policy",
            "mcp__investigation-tools__list_staff",
        ],
        permission_mode="bypassPermissions",
    )


async def run(event_id: str) -> str:
    """Suggest investigation notes for a specific event."""
    results = []
    options = build_options(event_id)

    async for message in query(
        prompt=(
            f"Suggest investigation notes for event {event_id}. "
            "Read the event details including linked policies and risks, "
            "then provide a structured investigation approach with best practice references "
            "from NICE, NHS England, MHRA, and CQC as appropriate."
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
        print("Usage: python -m agents.suggest_investigation <event_id>")
        sys.exit(1)
    print(f"Suggesting investigation for event {sys.argv[1]}...")
    summary = anyio.run(run, sys.argv[1])
    print(summary)
