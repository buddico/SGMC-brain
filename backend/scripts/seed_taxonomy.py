"""Seed the full GP practice event taxonomy from the canonical SGMC Data Manager JSON.

Imports all 119 event types across 14 categories. Types that already have
custom JSON schemas (significant-event, near-miss, violent-patient-incident,
supplier-incident) keep their schemas. All other types get a generic schema.

Run: python scripts/seed_taxonomy.py
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

# Canonical taxonomy (copied from SGMC Data Manager)
# Works both in Docker (/app/seed-data/) and locally (../../seed-data/)
_SEED_DATA = Path("/app/seed-data") if Path("/app/seed-data").exists() else Path(__file__).parent.parent.parent / "seed-data"
TAXONOMY_FILE = _SEED_DATA / "gp_practice_event_taxonomy.json"
CUSTOM_SCHEMA_DIR = _SEED_DATA / "event-types"

# Map taxonomy IDs to existing slugs (so we update rather than duplicate)
EXISTING_SLUG_MAP = {
    "significant-events-seas": "significant-event",
    "near-misses": "near-miss",
    # violent-patient-incident maps to multiple taxonomy IDs
    "physical-violence": "violent-patient-incident",
    "verbal-abuse-threats": None,  # separate type in taxonomy
    # supplier-incident covers multiple taxonomy IDs
    "phone-system-outage": None,
    "clinical-system-downtime": None,
}

# CQC domain string to normalised value
CQC_MAP = {
    "Safe": "safe",
    "Effective": "effective",
    "Responsive": "responsive",
    "Caring": "caring",
    "Well-led": "well_led",
}


def normalise_cqc(domain_str: str) -> str:
    """Take 'Safe, Effective' -> 'safe' (use first domain)."""
    first = domain_str.split(",")[0].strip()
    return CQC_MAP.get(first, first.lower().replace("-", "_"))


def to_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def build_generic_schema(event_type: dict, category_name: str) -> dict:
    """Build a generic JSON schema for event types without custom schemas."""
    name = event_type["name"]
    examples = event_type.get("examples", [])
    example_text = ", ".join(examples[:3]) if examples else ""

    return {
        "type": "object",
        "properties": {
            "event_title": {
                "type": "string",
                "title": "Event Title",
                "description": f"Brief summary of the {name.lower()}"
            },
            "date_of_incident": {
                "type": "string",
                "format": "date-time",
                "title": "Date & Time of Incident"
            },
            "description": {
                "type": "string",
                "title": "What Happened?",
                "description": f"Describe what happened in detail. Examples: {example_text}" if example_text else "Describe what happened in detail.",
                "minLength": 20
            },
            "severity": {
                "type": "string",
                "title": "Severity",
                "enum": ["minor", "moderate", "severe", "catastrophic"],
                "enumNames": [
                    "Minor (no harm)",
                    "Moderate (minor harm)",
                    "Severe (major harm)",
                    "Catastrophic (death/permanent harm)"
                ]
            },
            "immediate_actions": {
                "type": "string",
                "title": "Immediate Actions Taken",
                "description": "What was done immediately in response?",
                "minLength": 10
            },
            "contributing_factors": {
                "type": "string",
                "title": "Contributing Factors",
                "description": "What factors contributed to this event?"
            },
            "patient_involved": {
                "type": "boolean",
                "title": "Patient Involved?",
                "default": False
            },
        },
        "required": ["event_title", "date_of_incident", "description", "severity"]
    }


def build_generic_ui_schema() -> dict:
    return {
        "description": {"ui:widget": "textarea", "ui:options": {"rows": 5}},
        "immediate_actions": {"ui:widget": "textarea", "ui:options": {"rows": 3}},
        "contributing_factors": {"ui:widget": "textarea", "ui:options": {"rows": 3}},
    }


def load_custom_schema(slug: str) -> tuple[dict, dict | None] | None:
    """Load a custom JSON schema file if it exists."""
    json_file = CUSTOM_SCHEMA_DIR / f"{slug}.json"
    if not json_file.exists():
        return None
    with open(json_file) as f:
        data = json.load(f)
    return data.get("json_schema", {}), data.get("ui_schema")


def seed_taxonomy(db: Session):
    if not TAXONOMY_FILE.exists():
        print(f"ERROR: Taxonomy file not found: {TAXONOMY_FILE}")
        print("Make sure SGMC Data Manager is at the expected path.")
        sys.exit(1)

    with open(TAXONOMY_FILE) as f:
        taxonomy = json.load(f)

    categories = taxonomy["categories"]
    created = 0
    updated = 0
    display_order = 0

    for cat in categories:
        cat_name = cat["name"]
        cqc = normalise_cqc(cat.get("cqc_domain", ""))

        for et in cat["event_types"]:
            display_order += 1
            slug = to_slug(et["name"])
            examples = et.get("examples", [])
            typical_actions = et.get("typical_actions", [])

            # Check if this type already exists
            existing = db.query(EventType).filter(EventType.slug == slug).first()

            if existing:
                # Update existing with category info
                existing.category = cat_name
                existing.display_order = display_order
                existing.examples = examples
                existing.typical_actions = typical_actions
                if not existing.cqc_category:
                    existing.cqc_category = cqc
                updated += 1
                continue

            # Check if it maps to an existing custom type
            # (e.g. "Significant Events (SEAs)" -> "significant-event")
            custom_slug = EXISTING_SLUG_MAP.get(et["id"])
            if custom_slug:
                existing = db.query(EventType).filter(EventType.slug == custom_slug).first()
                if existing:
                    existing.category = cat_name
                    existing.display_order = display_order
                    existing.examples = examples
                    existing.typical_actions = typical_actions
                    if not existing.cqc_category:
                        existing.cqc_category = cqc
                    updated += 1
                    continue

            # Try loading custom schema, otherwise use generic
            custom = load_custom_schema(slug)
            if custom:
                json_schema, ui_schema = custom
            else:
                json_schema = build_generic_schema(et, cat_name)
                ui_schema = build_generic_ui_schema()

            # Build tags from category and examples
            tags = [to_slug(cat_name)]
            if examples:
                tags.extend([to_slug(ex) for ex in examples[:2]])

            event_type = EventType(
                name=et["name"],
                slug=slug,
                description=f"{et.get('examples_raw', et['name'])}",
                version="1.0.0",
                json_schema=json_schema,
                ui_schema=ui_schema,
                category=cat_name,
                display_order=display_order,
                tags=tags,
                examples=examples,
                typical_actions=typical_actions,
                cqc_category=cqc,
                created_by="seed-taxonomy@sgmc-brain",
            )
            db.add(event_type)
            created += 1

    db.commit()
    print(f"Taxonomy seeded: {created} created, {updated} updated")
    print(f"Total event types: {db.query(EventType).count()}")


if __name__ == "__main__":
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        seed_taxonomy(db)
