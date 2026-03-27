"""Seed staff from SGMC Practice Profile.

Run: python scripts/seed_staff.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base
from app.models.user import Role, User, user_roles

STAFF = [
    # Leadership
    {"name": "Dr Anjan Chakraborty", "email": "anjan.chakraborty@nhs.net", "job_title": "GP Principal", "is_clinical": True, "role": "partner"},
    {"name": "Amy Cox", "email": "amy.cox5@nhs.net", "job_title": "Practice Manager", "is_clinical": False, "role": "manager"},
    {"name": "Ramune Cerkesiene", "email": "ramune.cerkesiene2@nhs.net", "job_title": "Operations Manager", "is_clinical": False, "role": "manager"},
    # Salaried GPs
    {"name": "Dr Purwa Wilson", "email": "purwa.wilson@nhs.net", "job_title": "Salaried GP", "is_clinical": True, "role": "gp"},
    {"name": "Dr Alessia Corrieri", "email": "alessia.corrieri3@nhs.net", "job_title": "Salaried GP", "is_clinical": True, "role": "gp"},
    # Locum GPs
    {"name": "Dr Benal Arslan", "email": "b.arslan@nhs.net", "job_title": "Locum GP", "is_clinical": True, "role": "gp"},
    {"name": "Dr Ajay Bassi", "email": "a.bassi@nhs.net", "job_title": "Locum GP", "is_clinical": True, "role": "gp"},
    {"name": "Dr Aly Gheita", "email": "a.gheita@nhs.net", "job_title": "Locum GP", "is_clinical": True, "role": "gp"},
    {"name": "Dr Rebecca Olowookere", "email": "r.olowookere@nhs.net", "job_title": "Locum GP", "is_clinical": True, "role": "gp"},
    {"name": "Dr Tarun Pratap", "email": "tarun.pratap1@nhs.net", "job_title": "Locum GP", "is_clinical": True, "role": "gp"},
    {"name": "Dr Fatima Shaik", "email": "f.shaik@nhs.net", "job_title": "Locum GP", "is_clinical": True, "role": "gp"},
    {"name": "Dr Yuji Suzuki", "email": "yuji.suzuki@nhs.net", "job_title": "Locum GP", "is_clinical": True, "role": "gp"},
    # Nurse
    {"name": "Kaydeen Johnson", "email": "kaydeen.johnson@nhs.net", "job_title": "Practice Nurse", "is_clinical": True, "role": "clinical"},
    # HCA
    {"name": "Cristine Atienza", "email": "c.atienza1@nhs.net", "job_title": "Healthcare Assistant", "is_clinical": True, "role": "clinical"},
    # Pharmacist
    {"name": "Chandni Shah", "email": "chandni.shah7@nhs.net", "job_title": "Clinical Pharmacist", "is_clinical": True, "role": "clinical"},
    # PAs
    {"name": "Zakir Ali", "email": "zakir.ali@nhs.net", "job_title": "Physician Associate", "is_clinical": True, "role": "clinical"},
    {"name": "Lucas Posso Romo", "email": "l.possoromo@nhs.net", "job_title": "Physician Associate", "is_clinical": True, "role": "clinical"},
    # Admin
    {"name": "Marina Skaros", "email": "marinaskaros@nhs.net", "job_title": "Patient Services Lead", "is_clinical": False, "role": "reception"},
    {"name": "Madeha Ahmed", "email": "madeha.ahmed1@nhs.net", "job_title": "Receptionist", "is_clinical": False, "role": "reception"},
    {"name": "Mark Bennett", "email": "mark.bennett18@nhs.net", "job_title": "Receptionist", "is_clinical": False, "role": "reception"},
    {"name": "Anthea George", "email": "anthea.george@nhs.net", "job_title": "Receptionist", "is_clinical": False, "role": "reception"},
    {"name": "Farah Hashim", "email": "farah.hashim@nhs.net", "job_title": "Receptionist", "is_clinical": False, "role": "reception"},
    {"name": "Tina Liddiard", "email": "tina.liddiard@nhs.net", "job_title": "Receptionist / Care Coordinator", "is_clinical": False, "role": "reception"},
    {"name": "Geraldine McFadzean", "email": "geraldine.mcfadzean@nhs.net", "job_title": "Receptionist", "is_clinical": False, "role": "reception"},
    {"name": "Chanel Smith", "email": "chanel.smith1@nhs.net", "job_title": "Receptionist", "is_clinical": False, "role": "reception"},
    {"name": "Eleni Stravogianis", "email": "eleni.stravogianis@nhs.net", "job_title": "Receptionist", "is_clinical": False, "role": "reception"},
    {"name": "Elena Zanin", "email": "e.zanin@nhs.net", "job_title": "Receptionist", "is_clinical": False, "role": "reception"},
    {"name": "Rebecca Ward", "email": "rebecca.ward15@nhs.net", "job_title": "Receptionist", "is_clinical": False, "role": "reception"},
    {"name": "Natalija Konoreva", "email": "natalija.konoreva@nhs.net", "job_title": "Receptionist", "is_clinical": False, "role": "reception"},
]


def seed_staff(db: Session):
    count = 0
    for s in STAFF:
        existing = db.query(User).filter(User.email == s["email"]).first()
        if existing:
            continue

        role = db.query(Role).filter(Role.name == s["role"]).first()
        user = User(
            name=s["name"],
            email=s["email"],
            job_title=s["job_title"],
            is_clinical=s["is_clinical"],
            is_active=True,
        )
        if role:
            user.roles.append(role)
        db.add(user)
        count += 1

    db.commit()
    print(f"Seeded {count} staff members")


if __name__ == "__main__":
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        seed_staff(db)
