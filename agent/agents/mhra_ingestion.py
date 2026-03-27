"""MHRA Ingestion Agent - polls GOV.UK for new safety alerts and ingests them."""

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
from tools.brain_api import create_alert, list_alerts
from tools.govuk import fetch_govuk_content, search_govuk_alerts

SYSTEM_PROMPT = """You are the MHRA Ingestion Agent for Stroud Green Medical Clinic.

## Task
Ingest new MHRA alerts from GOV.UK into the system. Be EFFICIENT — minimise tool calls.

## Steps
1. `list_alerts` to get existing content_ids (for dedup).
2. `search_govuk_alerts` with document_type="medical_safety_alert" count=10.
3. `search_govuk_alerts` with document_type="drug_safety_update" count=10.
4. For each result NOT already in system (match content_id), call `create_alert` IMMEDIATELY using data from the search results. Do NOT fetch full content — use the title and description from search results as the summary.
   - source: "mhra_drug" for drug/device alerts, "drug_safety_update" for DSUs
   - issued_date: use the published date from search results
   - severity: "high" for recalls, "medium" for warnings, "low" for updates
5. Report count of new alerts created.

## CRITICAL: Create alerts from search results directly. Do NOT call fetch_govuk_content — it wastes budget.
"""


def build_options() -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(
        name="mhra-tools",
        version="1.0.0",
        tools=[search_govuk_alerts, fetch_govuk_content, list_alerts, create_alert],
    )

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=config.HAIKU_MODEL,
        max_turns=15,
        max_budget_usd=config.MAX_BUDGET_INGESTION,
        mcp_servers={"mhra-tools": server},
        allowed_tools=[
            "mcp__mhra-tools__search_govuk_alerts",
            "mcp__mhra-tools__fetch_govuk_content",
            "mcp__mhra-tools__list_alerts",
            "mcp__mhra-tools__create_alert",
        ],
        permission_mode="bypassPermissions",
    )


async def run() -> str:
    """Run the MHRA ingestion agent. Returns a summary of what happened."""
    results = []
    options = build_options()

    async for message in query(
        prompt="Check GOV.UK for new MHRA drug/device alerts and drug safety updates. Ingest any new ones.",
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
    print("Running MHRA Ingestion Agent...")
    summary = anyio.run(run)
    print(summary)
