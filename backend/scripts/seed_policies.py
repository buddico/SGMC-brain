"""Seed policies from the 54 customised .docx files in SGMC Data Manager.

Maps each .docx filename to a policy domain and CQC key questions based on
the SGMC Policy Framework (28 core + additional policies).

Run: python scripts/seed_policies.py
"""

import os
import re
import sys
from datetime import date
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base
from app.models.policy import CQCKeyQuestion, Policy, PolicyCQCMapping, PolicyDomain, PolicyStatus

# Map policy filenames to domains
DOMAIN_MAP = {
    # Patient Access
    "Appointment Access and Triage": PolicyDomain.PATIENT_ACCESS,
    "Patient Registration": PolicyDomain.PATIENT_ACCESS,
    "Home Visits": PolicyDomain.PATIENT_ACCESS,
    "Out of Hours and Extended Access": PolicyDomain.PATIENT_ACCESS,
    "Appointment Punctuality": PolicyDomain.PATIENT_ACCESS,
    "DNA Management": PolicyDomain.PATIENT_ACCESS,
    # Clinical Safety
    "Red Flag and Clinical Escalation": PolicyDomain.CLINICAL_SAFETY,
    "Mental Health Crisis": PolicyDomain.CLINICAL_SAFETY,
    "Safeguarding Children and Adults": PolicyDomain.CLINICAL_SAFETY,
    "Prescribing and Medication Safety": PolicyDomain.CLINICAL_SAFETY,
    "Medical Equipment and Cold Chain": PolicyDomain.CLINICAL_SAFETY,
    "Zero Tolerance and Violent Patients": PolicyDomain.CLINICAL_SAFETY,
    "Vulnerable Patients": PolicyDomain.CLINICAL_SAFETY,
    # Clinical Quality
    "Test Results Management": PolicyDomain.CLINICAL_QUALITY,
    "Clinical Supervision and Scope of Practice": PolicyDomain.CLINICAL_QUALITY,
    "Significant Event Analysis and Learning": PolicyDomain.CLINICAL_QUALITY,
    "QOF and Disease Management": PolicyDomain.CLINICAL_QUALITY,
    "Clinical Governance": PolicyDomain.CLINICAL_QUALITY,
    "Consent to Care and Treatment": PolicyDomain.CLINICAL_QUALITY,
    "Duty of Candour": PolicyDomain.CLINICAL_QUALITY,
    "Chaperone": PolicyDomain.CLINICAL_QUALITY,
    # Information Governance
    "Data Protection and GDPR": PolicyDomain.INFORMATION_GOVERNANCE,
    "Subject Access Requests": PolicyDomain.INFORMATION_GOVERNANCE,
    "Confidentiality and Information Sharing": PolicyDomain.INFORMATION_GOVERNANCE,
    # Patient Experience
    "Complaints Management": PolicyDomain.PATIENT_EXPERIENCE,
    "Patient Communication": PolicyDomain.PATIENT_EXPERIENCE,
    "Patient Records and Change of Details": PolicyDomain.PATIENT_EXPERIENCE,
    "Accessible Information and Reasonable Adjustments": PolicyDomain.PATIENT_EXPERIENCE,
    "Carers": PolicyDomain.PATIENT_EXPERIENCE,
    # IPC & Health Safety
    "Infection Prevention and Control": PolicyDomain.IPC_HEALTH_SAFETY,
    "Staff Immunisation and Occupational Health": PolicyDomain.IPC_HEALTH_SAFETY,
    "Health and Safety Management": PolicyDomain.IPC_HEALTH_SAFETY,
    "Fire Safety": PolicyDomain.IPC_HEALTH_SAFETY,
    "Display Screen Equipment and Eye Testing": PolicyDomain.IPC_HEALTH_SAFETY,
    "Sexual Safety": PolicyDomain.IPC_HEALTH_SAFETY,
    # Workforce
    "Recruitment": PolicyDomain.WORKFORCE,
    "Training and Development": PolicyDomain.WORKFORCE,
    "Homeworking and Remote Working": PolicyDomain.WORKFORCE,
    "Staff Conduct Disciplinary and Grievance": PolicyDomain.WORKFORCE,
    "Staff Leave Absence and Working Hours": PolicyDomain.WORKFORCE,
    "Staff Wellbeing": PolicyDomain.WORKFORCE,
    # Business Resilience
    "Business Continuity": PolicyDomain.BUSINESS_RESILIENCE,
    "Death Notification and Bereavement": PolicyDomain.BUSINESS_RESILIENCE,
    "Succession Plan": PolicyDomain.BUSINESS_RESILIENCE,
    # Governance
    "Freedom to Speak Up": PolicyDomain.GOVERNANCE,
    "Financial Governance": PolicyDomain.GOVERNANCE,
    "Fraud Prevention": PolicyDomain.GOVERNANCE,
    "Equality Diversity and Inclusion": PolicyDomain.GOVERNANCE,
    "Third Party and Partnership Governance": PolicyDomain.GOVERNANCE,
    "Vision Mission and Values": PolicyDomain.GOVERNANCE,
    "Carbon Reduction Plan": PolicyDomain.GOVERNANCE,
}

# Policy leads from the framework
POLICY_LEADS = {
    "Appointment Access and Triage": ("amy.cox@stroudgreenmedical.co.uk", "Amy Cox"),
    "Red Flag and Clinical Escalation": ("anjan.chakraborty@nhs.net", "Dr Chakraborty"),
    "Mental Health Crisis": ("anjan.chakraborty@nhs.net", "Dr Chakraborty"),
    "Safeguarding Children and Adults": ("anjan.chakraborty@nhs.net", "Dr Chakraborty"),
    "Prescribing and Medication Safety": ("anjan.chakraborty@nhs.net", "Dr Chakraborty"),
    "Complaints Management": ("amy.cox@stroudgreenmedical.co.uk", "Amy Cox"),
    "Significant Event Analysis and Learning": ("anjan.chakraborty@nhs.net", "Dr Chakraborty"),
    "Infection Prevention and Control": ("kaydeen.johnson@stroudgreenmedical.co.uk", "Kaydeen Johnson"),
    "Recruitment": ("ramune.cerkesiene@stroudgreenmedical.co.uk", "Ramune Cerkesiene"),
    "Business Continuity": ("amy.cox@stroudgreenmedical.co.uk", "Amy Cox"),
    "Fire Safety": ("amy.cox@stroudgreenmedical.co.uk", "Amy Cox"),
    "Health and Safety Management": ("amy.cox@stroudgreenmedical.co.uk", "Amy Cox"),
    "Training and Development": ("amy.cox@stroudgreenmedical.co.uk", "Amy Cox"),
}


def to_slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:300]


def seed_policies(db: Session, policy_dir: str | None = None):
    """Seed policies from .docx filenames."""

    # If a directory of .docx files is provided, use filenames
    docx_files: list[str] = []
    if policy_dir and os.path.isdir(policy_dir):
        docx_files = [f for f in os.listdir(policy_dir) if f.endswith(".docx")]
    else:
        # Use the domain map keys as policy names
        docx_files = [f"{name} Policy.docx" for name in DOMAIN_MAP.keys()]

    count = 0
    for filename in sorted(docx_files):
        title = filename.replace(".docx", "").strip()
        # Try to match to domain map
        domain = None
        for key, dom in DOMAIN_MAP.items():
            if key.lower() in title.lower():
                domain = dom
                break
        if domain is None:
            domain = PolicyDomain.GOVERNANCE  # default

        slug = to_slug(title)

        # Check if already exists
        existing = db.query(Policy).filter(Policy.slug == slug).first()
        if existing:
            continue

        lead = POLICY_LEADS.get(title.replace(" Policy", ""), (None, None))

        policy = Policy(
            title=title,
            slug=slug,
            domain=domain,
            status=PolicyStatus.ACTIVE,
            policy_lead_email=lead[0],
            policy_lead_name=lead[1],
            review_frequency_months=12,
            last_reviewed=date(2026, 2, 1),
            next_review_due=date(2027, 2, 1),
            docx_path=filename if policy_dir else None,
            created_by="seed@sgmc-brain",
        )
        db.add(policy)
        count += 1

    db.commit()
    print(f"Seeded {count} policies")


if __name__ == "__main__":
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        # Try to find the policy docx directory
        policy_dir = os.environ.get(
            "POLICY_DIR",
            "/Users/anjan/Programs/Cursor/SGMC Data Manager/policies/custom-policies",
        )
        seed_policies(db, policy_dir)
