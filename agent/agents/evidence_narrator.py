"""Evidence Narrator Agent - generates CQC-ready narrative summaries from evidence packs."""

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
from tools.brain_api import get_dashboard_stats, get_evidence_pack, list_events, list_risks

SYSTEM_PROMPT = """You are the Evidence Narrator for Stroud Green Medical Clinic's CQC governance system (SGMC Brain).

Your job is to take structured evidence data and write a clear, professional narrative that CQC inspectors can read. This is the kind of summary a Practice Manager would normally spend hours writing before a CQC visit.

## Output format

Write in formal but accessible English, structured under CQC's 5 key questions:
1. Safe
2. Effective
3. Caring
4. Responsive
5. Well-led

For each section:
- State the number of relevant policies and their review status
- Summarise any significant events, what was learned, and what changed
- Note relevant risks and how they're being managed
- Highlight the learning loop: event → investigation → discussion → action → improvement
- Flag any gaps or areas for improvement honestly (CQC values self-awareness)

## Rules
- Write in third person ("The practice..." not "We...")
- Use specific numbers and dates, not vague language
- Keep the total narrative under 2000 words
- Do not fabricate data — only use what the evidence pack contains
- If data is missing (e.g. no events discussed at meetings), note it as an area for development
- No patient identifiable information
"""


def build_options() -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(
        name="narrator-tools",
        version="1.0.0",
        tools=[get_evidence_pack, get_dashboard_stats, list_events, list_risks],
    )

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=config.SONNET_MODEL,
        max_turns=8,
        max_budget_usd=config.MAX_BUDGET_NARRATOR,
        mcp_servers={"narrator-tools": server},
        allowed_tools=[
            "mcp__narrator-tools__get_evidence_pack",
            "mcp__narrator-tools__get_dashboard_stats",
            "mcp__narrator-tools__list_events",
            "mcp__narrator-tools__list_risks",
        ],
        permission_mode="bypassPermissions",
    )


async def run(pack_id: str) -> str:
    """Generate a narrative summary for an evidence pack. Returns the narrative text."""
    results = []
    options = build_options()

    async for message in query(
        prompt=(
            f"Read evidence pack {pack_id} and write a CQC-ready narrative summary. "
            "Structure it under the 5 key questions. Include specific numbers and dates. "
            "Be honest about gaps."
        ),
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    results.append(block.text)
        elif isinstance(message, ResultMessage):
            results.append(f"\n---\n[Cost: ${message.total_cost_usd:.4f}]")

    return "\n".join(results)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m agents.evidence_narrator <pack_id>")
        sys.exit(1)
    print(f"Generating narrative for pack {sys.argv[1]}...")
    narrative = anyio.run(run, sys.argv[1])
    print(narrative)
