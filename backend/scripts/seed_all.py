"""Run all seed scripts in order.

Run: python scripts/seed_all.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base

from scripts.seed_roles import seed_roles
from scripts.seed_policies import seed_policies
from scripts.seed_event_types import seed_event_types


def main():
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)

    policy_dir = os.environ.get(
        "POLICY_DIR",
        "/Users/anjan/Programs/Cursor/SGMC Data Manager/policies/custom-policies",
    )

    with Session(engine) as db:
        print("=== Seeding roles and permissions ===")
        seed_roles(db)

        print("\n=== Seeding policies ===")
        seed_policies(db, policy_dir)

        print("\n=== Seeding event types ===")
        seed_event_types(db)

    print("\nDone! All seed data loaded.")


if __name__ == "__main__":
    main()
