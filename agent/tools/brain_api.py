"""MCP tools that call the SGMC Brain API. These are the agent's interface to the system of record."""

import json

import httpx
from claude_agent_sdk import tool

from config import config

API = config.BRAIN_API_URL


async def _api_get(path: str) -> dict | list:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{API}{path}")
        resp.raise_for_status()
        return resp.json()


async def _api_post(path: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{API}{path}", json=data)
        resp.raise_for_status()
        return resp.json()


async def _api_put(path: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.put(f"{API}{path}", json=data)
        resp.raise_for_status()
        return resp.json()


# --- Alert tools ---

@tool("list_alerts", "List existing alerts in the system. Use to check for duplicates before creating.", {"limit": int})
async def list_alerts(args: dict) -> dict:
    limit = args.get("limit", 100)
    alerts = await _api_get(f"/alerts?limit={limit}")
    return {"content": [{"type": "text", "text": json.dumps(alerts, indent=2)}]}


@tool("create_alert", "Create a new safety alert in the system.", {
    "source": str, "title": str, "summary": str, "url": str,
    "content_id": str, "issued_date": str, "message_type": str, "severity": str,
})
async def create_alert(args: dict) -> dict:
    # Filter out empty/None values
    data = {k: v for k, v in args.items() if v}
    result = await _api_post("/alerts", data)
    return {"content": [{"type": "text", "text": f"Alert created: {json.dumps(result)}"}]}


# --- Policy tools ---

@tool("list_policies", "List all active policies with title, domain, lead.", {"domain": str})
async def list_policies(args: dict) -> dict:
    params = "?status=active"
    if args.get("domain"):
        params += f"&domain={args['domain']}"
    policies = await _api_get(f"/policies{params}")
    summary = [{"id": p["id"], "title": p["title"], "domain": p["domain"], "lead": p.get("policy_lead_name")} for p in policies]
    return {"content": [{"type": "text", "text": json.dumps(summary, indent=2)}]}


@tool("get_policy", "Get full details of a specific policy.", {"policy_id": str})
async def get_policy(args: dict) -> dict:
    policy = await _api_get(f"/policies/{args['policy_id']}")
    return {"content": [{"type": "text", "text": json.dumps(policy, indent=2)}]}


# --- Event tools ---

@tool("get_event", "Get full details of an event including payload and links.", {"event_id": str})
async def get_event(args: dict) -> dict:
    event = await _api_get(f"/events/{args['event_id']}")
    return {"content": [{"type": "text", "text": json.dumps(event, indent=2)}]}


@tool("list_events", "List recent events with status and severity.", {"limit": int})
async def list_events(args: dict) -> dict:
    events = await _api_get(f"/events?limit={args.get('limit', 50)}")
    return {"content": [{"type": "text", "text": json.dumps(events, indent=2)}]}


@tool("update_event_links", "Link an event to policies and/or risks.", {
    "event_id": str, "linked_policy_ids": str, "linked_risk_ids": str,
})
async def update_event_links(args: dict) -> dict:
    data = {}
    if args.get("linked_policy_ids"):
        data["linked_policy_ids"] = json.loads(args["linked_policy_ids"]) if isinstance(args["linked_policy_ids"], str) else args["linked_policy_ids"]
    if args.get("linked_risk_ids"):
        data["linked_risk_ids"] = json.loads(args["linked_risk_ids"]) if isinstance(args["linked_risk_ids"], str) else args["linked_risk_ids"]
    result = await _api_put(f"/events/{args['event_id']}/links", data)
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


# --- Staff tools ---

@tool("list_staff", "List all practice staff with names, job titles, emails, and whether they are clinical.", {"_unused": str})
async def list_staff(args: dict) -> dict:
    staff = await _api_get("/staff")
    return {"content": [{"type": "text", "text": json.dumps(staff, indent=2)}]}


# --- Risk tools ---

@tool("list_risks", "List all risks with scores and status.", {"_unused": str})
async def list_risks(args: dict) -> dict:
    risks = await _api_get("/risks")
    summary = [{"id": r["id"], "ref": r["reference"], "title": r["title"], "score": r["risk_score"], "status": r["status"]} for r in risks]
    return {"content": [{"type": "text", "text": json.dumps(summary, indent=2)}]}


# --- Evidence tools ---

@tool("get_evidence_pack", "Get a CQC evidence pack with all sections.", {"pack_id": str})
async def get_evidence_pack(args: dict) -> dict:
    pack = await _api_get(f"/evidence/packs/{args['pack_id']}")
    return {"content": [{"type": "text", "text": json.dumps(pack, indent=2)}]}


@tool("get_dashboard_stats", "Get current governance dashboard statistics.", {"_unused": str})
async def get_dashboard_stats(args: dict) -> dict:
    stats = await _api_get("/evidence/dashboard")
    return {"content": [{"type": "text", "text": json.dumps(stats, indent=2)}]}
