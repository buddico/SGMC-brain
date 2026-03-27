"""Policy models - versioned policies with CQC mappings and staff acknowledgments."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PolicyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class PolicyDomain(str, enum.Enum):
    PATIENT_ACCESS = "patient_access"
    CLINICAL_SAFETY = "clinical_safety"
    CLINICAL_QUALITY = "clinical_quality"
    INFORMATION_GOVERNANCE = "information_governance"
    PATIENT_EXPERIENCE = "patient_experience"
    IPC_HEALTH_SAFETY = "ipc_health_safety"
    WORKFORCE = "workforce"
    BUSINESS_RESILIENCE = "business_resilience"
    GOVERNANCE = "governance"


class CQCKeyQuestion(str, enum.Enum):
    SAFE = "safe"
    EFFECTIVE = "effective"
    CARING = "caring"
    RESPONSIVE = "responsive"
    WELL_LED = "well_led"


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300))
    slug: Mapped[str] = mapped_column(String(300), unique=True)
    domain: Mapped[PolicyDomain] = mapped_column(Enum(PolicyDomain))
    status: Mapped[PolicyStatus] = mapped_column(Enum(PolicyStatus), default=PolicyStatus.DRAFT)

    # Ownership
    policy_lead_email: Mapped[str | None] = mapped_column(String(255))
    policy_lead_name: Mapped[str | None] = mapped_column(String(255))

    # Review cycle
    review_frequency_months: Mapped[int] = mapped_column(Integer, default=12)
    last_reviewed: Mapped[date | None] = mapped_column(Date)
    next_review_due: Mapped[date | None] = mapped_column(Date)

    # Content
    summary: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str | None] = mapped_column(Text)
    key_workflows: Mapped[dict | None] = mapped_column(JSONB)  # structured workflow data
    audit_checkpoints: Mapped[list | None] = mapped_column(JSONB)  # [{checkpoint, frequency, method, target}]

    # File references
    docx_path: Mapped[str | None] = mapped_column(String(500))  # path to .docx file

    # Metadata
    tags: Mapped[list | None] = mapped_column(JSONB, default=list)
    applicable_roles: Mapped[list | None] = mapped_column(JSONB, default=list)  # which roles need to know this

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by: Mapped[str | None] = mapped_column(String(255))
    updated_by: Mapped[str | None] = mapped_column(String(255))

    # Relationships
    versions: Mapped[list["PolicyVersion"]] = relationship(back_populates="policy", cascade="all, delete-orphan")
    cqc_mappings: Mapped[list["PolicyCQCMapping"]] = relationship(back_populates="policy", cascade="all, delete-orphan")
    acknowledgments: Mapped[list["PolicyAcknowledgment"]] = relationship(back_populates="policy", cascade="all, delete-orphan")


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id"))
    version: Mapped[str] = mapped_column(String(20))  # semver: 1.0.0, 1.1.0, etc.
    change_summary: Mapped[str | None] = mapped_column(Text)
    docx_path: Mapped[str | None] = mapped_column(String(500))
    content_snapshot: Mapped[dict | None] = mapped_column(JSONB)  # structured content at this version
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(255))

    policy: Mapped[Policy] = relationship(back_populates="versions")


class PolicyCQCMapping(Base):
    """Maps policies to CQC quality statements."""
    __tablename__ = "policy_cqc_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id"))
    key_question: Mapped[CQCKeyQuestion] = mapped_column(Enum(CQCKeyQuestion))
    quality_statement: Mapped[str] = mapped_column(String(200))  # e.g. "Learning culture"
    evidence_description: Mapped[str | None] = mapped_column(Text)

    policy: Mapped[Policy] = relationship(back_populates="cqc_mappings")


class PolicyAcknowledgment(Base):
    """Tracks staff acknowledgment of policy updates."""
    __tablename__ = "policy_acknowledgments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id"))
    user_email: Mapped[str] = mapped_column(String(255))
    user_name: Mapped[str] = mapped_column(String(255))
    version_acknowledged: Mapped[str] = mapped_column(String(20))
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    policy: Mapped[Policy] = relationship(back_populates="acknowledgments")
