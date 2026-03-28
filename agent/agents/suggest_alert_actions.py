"""Alert Action Suggestion Agent - suggests what the pharmacist/clinicians should do about a safety alert."""

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
from tools.brain_api import get_alert, get_policy, list_policies, list_risks, list_staff

SYSTEM_PROMPT = """You are the Alert Action Suggestion Agent for Stroud Green Medical Clinic (SGMC Brain).

Your job is to suggest specific actions for a safety alert (MHRA, NatPSA, CAS, Drug Safety Update) based on:
- The alert content (drug/device name, safety concern, affected patients)
- The practice's policies and current risk register
- Best practice from MHRA, BNF, NICE, NHS England
- The practice's staff and their roles

## Workflow

1. Use `get_alert` to read the full alert (title, summary, source, severity, message_type, pharmacist_notes).
   - **IMPORTANT**: If `pharmacist_notes` is present, this is the pharmacist's own summary of what's relevant — base your suggestions primarily on this field rather than the generic summary. The pharmacist has already interpreted the alert for the practice context.
2. Use `list_policies` to find policies related to the alert (e.g. prescribing, medicines management, IPC).
3. For each relevant policy, use `get_policy` to read the details and identify the policy lead.
4. Use `list_risks` to check if the alert relates to any existing risks.
5. Use `list_staff` to get all practice staff with roles.
6. Suggest 2-5 specific actions with named staff assignments.

## Staff assignment priority

1. **Pharmacist** — they triage alerts and handle medication-related actions (patient searches, formulary changes)
2. **Prescribing Lead / Clinical Lead** — for prescribing decisions, protocol changes
3. **Policy leads** for affected policies — they own the governance response
4. **Practice Manager** — for operational actions (procurement, supplier contact)
5. **Relevant clinical staff** — based on the alert type

## Best practice references

Ground suggestions in:
- **MHRA** — cite the alert itself and any MHRA action requirements
- **BNF** — for medication changes, alternative prescribing
- **NICE** — cite relevant guidelines (e.g., CG76 for medicines management)
- **NHS England** — Patient Safety Alert response framework
- **CQC** — Regulation 12 (Safe care and treatment), Regulation 17 (Good governance)

## Action format — output EXACTLY this format for each suggested action:
```
SUGGESTED_ACTION: [description] | ASSIGN: [staff name] | REASON: [why this person] | SOURCE: [source type and reference] | DEADLINE: [days from now, e.g. 7]
```

**SOURCE must be one of:**
- `MHRA: [the alert title/ref]` — when action stems directly from the alert
- `POLICY: [policy title]` — when action stems from a practice policy
- `NICE: [guideline ref]` — e.g. "NICE: CG76 - Medicines management"
- `BNF: [reference]` — for prescribing changes
- `CQC: [standard]` — e.g. "CQC: Regulation 12 - Safe care and treatment"
- `Best practice` — only when no specific source can be cited

## Common action types for alerts
- **Patient search**: Identify affected patients using clinical system (EMIS)
- **Medication review**: Review prescriptions for affected drug/device
- **Stock check**: Check practice stock for recalled items
- **Protocol update**: Update prescribing protocols or formulary
- **Patient contact**: Notify affected patients
- **Supplier action**: Contact supplier for recalls/returns
- **Staff briefing**: Inform relevant clinicians about the alert
- **Risk register update**: Add or update a risk entry

## Rules
- Suggest 2-5 actions per alert
- Always assign to named staff from the staff list
- Be specific about WHAT needs to be done and WHY
- Set urgent deadlines (1-2 days) for recalls and patient safety issues
- Set standard deadlines (7-14 days) for routine updates
"""


def build_options() -> ClaudeAgentOptions:
    server = create_sdk_mcp_server(
        name="alert-tools",
        version="1.0.0",
        tools=[get_alert, list_policies, get_policy, list_risks, list_staff],
    )

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=config.SONNET_MODEL,
        max_turns=10,
        max_budget_usd=config.MAX_BUDGET_ALERT_ACTIONS,
        mcp_servers={"alert-tools": server},
        allowed_tools=[
            "mcp__alert-tools__get_alert",
            "mcp__alert-tools__list_policies",
            "mcp__alert-tools__get_policy",
            "mcp__alert-tools__list_risks",
            "mcp__alert-tools__list_staff",
        ],
        permission_mode="bypassPermissions",
    )


async def run(alert_id: str) -> str:
    """Suggest actions for a specific alert."""
    results = []
    options = build_options()

    async for message in query(
        prompt=(
            f"Suggest actions for alert {alert_id}. "
            "Read the alert details, find relevant policies and risks, "
            "get the staff list, then suggest specific actions with named staff assignments. "
            "Ground your suggestions in MHRA guidance, BNF, NICE, or CQC best practice. "
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
        print("Usage: python -m agents.suggest_alert_actions <alert_id>")
        sys.exit(1)
    print(f"Suggesting actions for alert {sys.argv[1]}...")
    summary = anyio.run(run, sys.argv[1])
    print(summary)
