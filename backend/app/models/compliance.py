"""Compliance check models - training matrix, mandatory checks, document tracking."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CheckCategory(str, enum.Enum):
    MANDATORY_COMPLIANCE = "mandatory_compliance"
    TRAINING = "training"
    IT_ACCESS = "it_access"
    ONBOARDING = "onboarding"
    HR = "hr"
    CLINICAL = "clinical"
    EQUIPMENT = "equipment"
    PREMISES = "premises"


class CheckTemplate(Base):
    """Defines what checks exist and who they apply to."""
    __tablename__ = "check_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[CheckCategory] = mapped_column(Enum(CheckCategory))
    frequency_months: Mapped[int] = mapped_column(Integer, default=0)  # 0 = one-off
    requires_document: Mapped[bool] = mapped_column(Boolean, default=False)
    document_description: Mapped[str | None] = mapped_column(String(500))

    # Role-based applicability
    applicable_roles: Mapped[list | None] = mapped_column(JSONB, default=list)  # ["clinical", "admin", "management"]
    applicable_job_titles: Mapped[list | None] = mapped_column(JSONB)  # specific titles if needed

    # CQC relevance
    cqc_relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    cqc_quality_statement: Mapped[str | None] = mapped_column(String(200))

    # Linked policy
    linked_policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id"))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by: Mapped[str | None] = mapped_column(String(255))

    staff_checks: Mapped[list["StaffCheck"]] = relationship(back_populates="check_template")


class StaffCheck(Base):
    """Tracks completion of a check for a specific staff member."""
    __tablename__ = "staff_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    check_template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("check_templates.id"))
    staff_email: Mapped[str] = mapped_column(String(255))
    staff_name: Mapped[str] = mapped_column(String(255))
    completed_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    completed_by: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    check_template: Mapped[CheckTemplate] = relationship(back_populates="staff_checks")
    documents: Mapped[list["CheckDocument"]] = relationship(back_populates="staff_check", cascade="all, delete-orphan")


class CheckDocument(Base):
    """Evidence documents attached to staff checks."""
    __tablename__ = "check_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_check_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("staff_checks.id"))
    filename: Mapped[str] = mapped_column(String(300))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    uploaded_by: Mapped[str | None] = mapped_column(String(255))

    staff_check: Mapped[StaffCheck] = relationship(back_populates="documents")
