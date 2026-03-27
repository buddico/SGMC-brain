"""Seed RBAC roles and permissions.

Run: python scripts/seed_roles.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base
from app.models.user import Permission, Role

ROLES = [
    {"name": "reception", "display_name": "Reception / Admin", "level": 0},
    {"name": "clinical", "display_name": "Clinical Staff", "level": 10},
    {"name": "gp", "display_name": "GP", "level": 20},
    {"name": "manager", "display_name": "Practice Manager", "level": 30},
    {"name": "partner", "display_name": "Partner / Lead", "level": 40},
]

RESOURCES = ["policies", "events", "risks", "compliance", "alerts", "evidence", "users", "settings"]
ACTIONS = ["read", "write", "approve", "admin"]

# Role -> allowed (resource, action) pairs
ROLE_PERMISSIONS = {
    "reception": [
        ("policies", "read"), ("events", "read"), ("events", "write"),
        ("compliance", "read"), ("alerts", "read"),
    ],
    "clinical": [
        ("policies", "read"), ("events", "read"), ("events", "write"),
        ("compliance", "read"), ("compliance", "write"), ("alerts", "read"),
        ("risks", "read"),
    ],
    "gp": [
        ("policies", "read"), ("policies", "write"),
        ("events", "read"), ("events", "write"), ("events", "approve"),
        ("compliance", "read"), ("compliance", "write"),
        ("alerts", "read"), ("alerts", "write"),
        ("risks", "read"), ("risks", "write"),
        ("evidence", "read"),
    ],
    "manager": [
        (r, a) for r in RESOURCES for a in ["read", "write", "approve"]
    ],
    "partner": [
        (r, a) for r in RESOURCES for a in ACTIONS
    ],
}


def seed_roles(db: Session):
    # Create permissions
    perm_map = {}
    for resource in RESOURCES:
        for action in ACTIONS:
            name = f"{resource}.{action}"
            existing = db.query(Permission).filter(Permission.name == name).first()
            if existing:
                perm_map[name] = existing
                continue
            perm = Permission(name=name, resource=resource, action=action)
            db.add(perm)
            db.flush()
            perm_map[name] = perm

    # Create roles
    for role_def in ROLES:
        existing = db.query(Role).filter(Role.name == role_def["name"]).first()
        if existing:
            continue
        role = Role(
            name=role_def["name"],
            display_name=role_def["display_name"],
            level=role_def["level"],
        )
        # Assign permissions
        perms = ROLE_PERMISSIONS.get(role_def["name"], [])
        for resource, action in perms:
            key = f"{resource}.{action}"
            if key in perm_map:
                role.permissions.append(perm_map[key])
        db.add(role)

    db.commit()
    print(f"Seeded {len(ROLES)} roles and {len(perm_map)} permissions")


if __name__ == "__main__":
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        seed_roles(db)
