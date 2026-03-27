"""Scheduler for recurring agent tasks."""

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from agents.mhra_ingestion import run as run_mhra_ingestion
from config import config

logger = logging.getLogger("agent.scheduler")


async def mhra_job():
    """Scheduled MHRA ingestion job."""
    logger.info(f"[{datetime.now().isoformat()}] Starting MHRA ingestion...")
    try:
        summary = await run_mhra_ingestion()
        logger.info(f"MHRA ingestion complete:\n{summary}")
    except Exception as e:
        logger.error(f"MHRA ingestion failed: {e}")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        mhra_job,
        trigger=IntervalTrigger(hours=config.MHRA_POLL_HOURS),
        id="mhra_ingestion",
        name="MHRA Alert Ingestion",
        replace_existing=True,
    )

    return scheduler
