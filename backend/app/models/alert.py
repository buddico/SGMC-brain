"""Alert models - MHRA drug/device alerts, NatPSA, CAS alerts."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AlertSource(str, enum.Enum):
    MHRA_DRUG = "mhra_drug"
    MHRA_DEVICE = "mhra_device"
    DRUG_SAFETY_UPDATE = "drug_safety_update"
    NATPSA = "natpsa"
    CAS = "cas"


class AlertStatus(str, enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    NOT_APPLICABLE = "not_applicable"


class AlertPriority(str, enum.Enum):
    P1_URGENT = "p1_urgent"
    P2_IMPORTANT = "p2_important"
    P3_ROUTINE = "p3_routine"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[AlertSource] = mapped_column(Enum(AlertSource))
    content_id: Mapped[str | None] = mapped_column(String(200))  # GOV.UK content_id for dedup
    slug: Mapped[str | None] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    html_content: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(1000))

    issued_date: Mapped[date | None] = mapped_column(Date)
    message_type: Mapped[str | None] = mapped_column(String(50))  # FSN, recall, DSU, etc.
    severity: Mapped[str | None] = mapped_column(String(50))

    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), default=AlertStatus.NEW)
    priority: Mapped[AlertPriority | None] = mapped_column(Enum(AlertPriority))
    due_date: Mapped[date | None] = mapped_column(Date)

    raw_json: Mapped[dict | None] = mapped_column(JSONB)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    actions: Mapped[list["AlertAction"]] = relationship(back_populates="alert", cascade="all, delete-orphan")
    notifications: Mapped[list["AlertNotification"]] = relationship(back_populates="alert", cascade="all, delete-orphan")


class AlertAction(Base):
    __tablename__ = "alert_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id"))
    action_type: Mapped[str] = mapped_column(String(100))  # reviewed, actioned, patient_search, etc.
    notes: Mapped[str | None] = mapped_column(Text)
    evidence_files: Mapped[list | None] = mapped_column(JSONB, default=list)
    performed_by_email: Mapped[str] = mapped_column(String(255))
    performed_by_name: Mapped[str] = mapped_column(String(255))
    performed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    patients_identified: Mapped[int | None] = mapped_column(Integer)
    applies_to_practice: Mapped[bool | None] = mapped_column()

    alert: Mapped[Alert] = relationship(back_populates="actions")


class AlertNotification(Base):
    __tablename__ = "alert_notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id"))
    channel: Mapped[str] = mapped_column(String(50))  # teams, email
    recipients: Mapped[list | None] = mapped_column(JSONB)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    external_message_id: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    alert: Mapped[Alert] = relationship(back_populates="notifications")
