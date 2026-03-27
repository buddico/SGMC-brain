"""Seed event types from JSON Schema files in seed-data/event-types/.

Run: python scripts/seed_event_types.py
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base
from app.models.event import EventType

SEED_DIR = Path(__file__).parent.parent.parent / "seed-data" / "event-types"

CQC_CATEGORY_MAP = {
    "significant-event": "safe",
    "near-miss": "safe",
    "violent-patient-incident": "safe",
    "supplier-incident": "well_led",
}


def to_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def seed_event_types(db: Session):
    count = 0
    for json_file in sorted(SEED_DIR.glob("*.json")):
        with open(json_file) as f:
            data = json.load(f)

        name = data.get("name", json_file.stem.replace("-", " ").title())
        slug = to_slug(name)

        existing = db.query(EventType).filter(EventType.slug == slug).first()
        if existing:
            continue

        event_type = EventType(
            name=name,
            slug=slug,
            description=data.get("description"),
            version=data.get("version", "1.0.0"),
            json_schema=data.get("json_schema", {}),
            ui_schema=data.get("ui_schema"),
            tags=data.get("tags", []),
            cqc_category=CQC_CATEGORY_MAP.get(slug),
            created_by="seed@sgmc-brain",
        )
        db.add(event_type)
        count += 1

    db.commit()
    print(f"Seeded {count} event types")


if __name__ == "__main__":
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        seed_event_types(db)
