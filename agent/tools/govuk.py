"""MCP tools for fetching MHRA alerts from GOV.UK APIs."""

import json

import httpx
from claude_agent_sdk import tool

from config import config


@tool("search_govuk_alerts", "Search GOV.UK for medical safety alerts or drug safety updates. Returns titles, URLs, content_ids.", {
    "document_type": str, "count": int,
})
async def search_govuk_alerts(args: dict) -> dict:
    doc_type = args.get("document_type", "medical_safety_alert")
    count = args.get("count", 20)

    params = {
        "filter_document_type": doc_type,
        "count": count,
        "order": "-public_timestamp",
        "fields": "title,link,content_id,public_timestamp,description",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(config.GOVUK_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("results", []):
        results.append({
            "title": item.get("title"),
            "url": f"https://www.gov.uk{item.get('link', '')}",
            "content_id": item.get("content_id"),
            "published": item.get("public_timestamp"),
            "description": item.get("description"),
        })

    return {"content": [{"type": "text", "text": json.dumps(results, indent=2)}]}


@tool("fetch_govuk_content", "Fetch full content of a GOV.UK page by path.", {"path": str})
async def fetch_govuk_content(args: dict) -> dict:
    path = args["path"].lstrip("/")
    url = f"{config.GOVUK_CONTENT_URL}/{path}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    details = data.get("details", {})
    body_parts = details.get("body", [])
    body_text = ""
    if isinstance(body_parts, list):
        body_text = "\n".join(part.get("content", "") for part in body_parts if isinstance(part, dict))
    elif isinstance(body_parts, str):
        body_text = body_parts

    result = {
        "title": data.get("title"),
        "content_id": data.get("content_id"),
        "document_type": data.get("document_type"),
        "first_published": data.get("first_published_at"),
        "updated": data.get("public_updated_at"),
        "description": data.get("description"),
        "body_preview": body_text[:2000] if body_text else None,
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
