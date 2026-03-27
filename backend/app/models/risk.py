"""Risk register models - NHS 5x5 matrix, linked to events and policies."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class RiskStatus(str, enum.Enum):
    OPEN = "open"
    MITIGATED = "mitigated"
    CLOSED = "closed"
    ESCALATED = "escalated"


class RiskCategory(str, enum.Enum):
    CLINICAL_SAFETY = "clinical_safety"
    STAFFING = "staffing"
    INFORMATION_GOVERNANCE = "information_governance"
    PREMISES = "premises"
    BUSINESS_CONTINUITY = "business_continuity"
    PATIENT_SAFETY = "patient_safety"
    FINANCIAL = "financial"
    REGULATORY = "regulatory"
    OPERATIONAL = "operational"
    REPUTATIONAL = "reputational"


class Risk(Base):
    __tablename__ = "risks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference: Mapped[str | None] = mapped_column(String(20), unique=True)  # RISK-001
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[RiskCategory] = mapped_column(Enum(RiskCategory))
    status: Mapped[RiskStatus] = mapped_column(Enum(RiskStatus), default=RiskStatus.OPEN)

    # NHS 5x5 risk matrix
    likelihood: Mapped[int] = mapped_column(Integer)  # 1-5: rare, unlikely, possible, likely, almost_certain
    impact: Mapped[int] = mapped_column(Integer)  # 1-5: negligible, minor, moderate, major, catastrophic
    risk_score: Mapped[int] = mapped_column(Integer)  # likelihood * impact

    # Controls and gaps
    existing_controls: Mapped[str | None] = mapped_column(Text)
    gaps_in_control: Mapped[str | None] = mapped_column(Text)

    # Ownership
    owner_email: Mapped[str] = mapped_column(String(255))
    owner_name: Mapped[str] = mapped_column(String(255))

    # Review cycle
    date_identified: Mapped[date] = mapped_column(Date)
    last_reviewed: Mapped[date | None] = mapped_column(Date)
    next_review_due: Mapped[date | None] = mapped_column(Date)

    # Linked entities
    linked_policy_ids: Mapped[list | None] = mapped_column(JSONB, default=list)
    linked_event_ids: Mapped[list | None] = mapped_column(JSONB, default=list)

    # Closure
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    closure_rationale: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by: Mapped[str | None] = mapped_column(String(255))

    reviews: Mapped[list["RiskReview"]] = relationship(back_populates="risk", cascade="all, delete-orphan")
    actions: Mapped[list["RiskAction"]] = relationship(back_populates="risk", cascade="all, delete-orphan")


class RiskReview(Base):
    """Quarterly (or more frequent) risk reviews with evidence trail."""
    __tablename__ = "risk_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("risks.id"))
    reviewed_by_email: Mapped[str] = mapped_column(String(255))
    reviewed_by_name: Mapped[str] = mapped_column(String(255))
    review_date: Mapped[date] = mapped_column(Date)
    likelihood_after: Mapped[int | None] = mapped_column(Integer)
    impact_after: Mapped[int | None] = mapped_column(Integer)
    score_after: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    meeting_reference: Mapped[str | None] = mapped_column(String(200))  # link to meeting minutes
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    risk: Mapped[Risk] = relationship(back_populates="reviews")


class RiskAction(Base):
    """Actions to mitigate risks."""
    __tablename__ = "risk_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("risks.id"))
    description: Mapped[str] = mapped_column(Text)
    assigned_to_email: Mapped[str | None] = mapped_column(String(255))
    assigned_to_name: Mapped[str | None] = mapped_column(String(255))
    target_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_by: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(255))

    risk: Mapped[Risk] = relationship(back_populates="actions")
