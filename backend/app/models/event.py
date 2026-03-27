"""Event models - JSON Schema-driven incident/event reporting with full audit trail."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EventSeverity(str, enum.Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CATASTROPHIC = "catastrophic"


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_INVESTIGATION = "under_investigation"
    DISCUSSED = "discussed"
    ACTIONS_ASSIGNED = "actions_assigned"
    CLOSED = "closed"


class EventType(Base):
    """Defines event types via JSON Schema. New types can be created without code changes."""
    __tablename__ = "event_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # JSON Schema definition for dynamic forms
    json_schema: Mapped[dict] = mapped_column(JSONB)
    ui_schema: Mapped[dict | None] = mapped_column(JSONB)

    # Categorization
    tags: Mapped[list | None] = mapped_column(JSONB, default=list)
    linked_policy_ids: Mapped[list | None] = mapped_column(JSONB, default=list)  # UUIDs of related policies
    applicable_roles: Mapped[list | None] = mapped_column(JSONB, default=list)

    # CQC
    cqc_category: Mapped[str | None] = mapped_column(String(50))  # safe, effective, etc.

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by: Mapped[str | None] = mapped_column(String(255))

    events: Mapped[list["Event"]] = relationship(back_populates="event_type")


class Event(Base):
    """An incident/event record. Payload stored as JSONB, validated against EventType schema."""
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("event_types.id"))
    reference: Mapped[str | None] = mapped_column(String(50))  # auto-generated: SE-2026-001

    # Core fields (extracted from payload for indexing)
    title: Mapped[str] = mapped_column(String(300))
    severity: Mapped[EventSeverity | None] = mapped_column(Enum(EventSeverity))
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus), default=EventStatus.DRAFT)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Full event data (validated against event_type.json_schema)
    payload: Mapped[dict] = mapped_column(JSONB)

    # Reporter
    reported_by_email: Mapped[str] = mapped_column(String(255))
    reported_by_name: Mapped[str] = mapped_column(String(255))

    # Staff involved in the event (captured before triage)
    involved_staff: Mapped[list | None] = mapped_column(JSONB, default=list)  # [{email, name, role}]

    # Investigation
    investigator_email: Mapped[str | None] = mapped_column(String(255))
    investigation_notes: Mapped[str | None] = mapped_column(Text)
    learning_outcomes: Mapped[str | None] = mapped_column(Text)

    # Meeting discussion
    discussed_at_meeting: Mapped[bool] = mapped_column(Boolean, default=False)
    meeting_date: Mapped[datetime | None] = mapped_column(DateTime)
    meeting_notes: Mapped[str | None] = mapped_column(Text)

    # Duty of candour
    duty_of_candour_required: Mapped[bool] = mapped_column(Boolean, default=False)
    duty_of_candour_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Linked entities
    linked_policy_ids: Mapped[list | None] = mapped_column(JSONB, default=list)
    linked_risk_ids: Mapped[list | None] = mapped_column(JSONB, default=list)

    # Hashed patient reference (no PHI stored)
    patient_ref_hash: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    event_type: Mapped[EventType] = relationship(back_populates="events")
    history: Mapped[list["EventHistory"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    actions: Mapped[list["EventAction"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class EventHistory(Base):
    """Append-only audit trail for every event change."""
    __tablename__ = "event_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"))
    action: Mapped[str] = mapped_column(String(50))  # created, updated, status_changed, etc.
    actor_email: Mapped[str] = mapped_column(String(255))
    actor_name: Mapped[str] = mapped_column(String(255))
    changes: Mapped[dict | None] = mapped_column(JSONB)  # diff of what changed
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    event: Mapped[Event] = relationship(back_populates="history")


class EventAction(Base):
    """Actions arising from events - tracked to completion."""
    __tablename__ = "event_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"))
    description: Mapped[str] = mapped_column(Text)
    assigned_to_email: Mapped[str | None] = mapped_column(String(255))
    assigned_to_name: Mapped[str | None] = mapped_column(String(255))
    deadline: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_by: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(255))

    event: Mapped[Event] = relationship(back_populates="actions")
