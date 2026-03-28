"""SGMC Brain Agent Runtime - entry point.

Runs the scheduled agents (MHRA ingestion) and exposes an HTTP API
for triggering on-demand agents (event triage, evidence narrator).
"""

import asyncio
import logging
import sys

from fastapi import FastAPI
from pydantic import BaseModel

from agents.event_triage import run as run_triage
from agents.suggest_investigation import run as run_suggest_investigation
from agents.suggest_actions import run as run_suggest_actions
from agents.suggest_alert_actions import run as run_suggest_alert_actions
from agents.evidence_narrator import run as run_narrator
from agents.mhra_ingestion import run as run_mhra
from config import config
from services.scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("agent")

app = FastAPI(title="SGMC Brain Agent Runtime", version="0.1.0")
scheduler = create_scheduler()


@app.on_event("startup")
async def startup():
    scheduler.start()
    logger.info(f"Agent runtime started. MHRA poll every {config.MHRA_POLL_HOURS}h.")
    logger.info(f"Brain API: {config.BRAIN_API_URL}")


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()


@app.get("/health")
def health():
    jobs = [
        {"id": job.id, "name": job.name, "next_run": str(job.next_run_time)}
        for job in scheduler.get_jobs()
    ]
    return {"status": "ok", "service": "agent-runtime", "scheduled_jobs": jobs}


@app.post("/run/mhra-ingestion")
async def trigger_mhra():
    """Manually trigger MHRA ingestion."""
    logger.info("Manual MHRA ingestion triggered")
    summary = await run_mhra()
    return {"status": "completed", "summary": summary}


class EventRequest(BaseModel):
    event_id: str


@app.post("/run/event-triage")
async def trigger_triage(body: EventRequest):
    """Triage a specific event — link relevant policies and risks."""
    logger.info(f"Event triage triggered for {body.event_id}")
    summary = await run_triage(body.event_id)
    return {"status": "completed", "event_id": body.event_id, "summary": summary}


@app.post("/run/suggest-investigation")
async def trigger_suggest_investigation(body: EventRequest):
    """Suggest investigation notes for an event."""
    logger.info(f"Investigation suggestion triggered for {body.event_id}")
    summary = await run_suggest_investigation(body.event_id)
    return {"status": "completed", "event_id": body.event_id, "summary": summary}


@app.post("/run/suggest-actions")
async def trigger_suggest_actions(body: EventRequest):
    """Suggest actions with staff assignments for an event."""
    logger.info(f"Action suggestion triggered for {body.event_id}")
    summary = await run_suggest_actions(body.event_id)
    return {"status": "completed", "event_id": body.event_id, "summary": summary}


class AlertRequest(BaseModel):
    alert_id: str


@app.post("/run/suggest-alert-actions")
async def trigger_suggest_alert_actions(body: AlertRequest):
    """Suggest actions for a safety alert."""
    logger.info(f"Alert action suggestion triggered for {body.alert_id}")
    summary = await run_suggest_alert_actions(body.alert_id)
    return {"status": "completed", "alert_id": body.alert_id, "summary": summary}


class NarratorRequest(BaseModel):
    pack_id: str


@app.post("/run/evidence-narrator")
async def trigger_narrator(body: NarratorRequest):
    """Generate a CQC narrative for an evidence pack."""
    logger.info(f"Evidence narrator triggered for pack {body.pack_id}")
    narrative = await run_narrator(body.pack_id)
    return {"status": "completed", "pack_id": body.pack_id, "narrative": narrative}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8091, reload=True)
