"""Audit log - append-only record of all system changes."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class AuditLog(Base):
    """Immutable audit trail for every significant action in the system."""
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    actor_email: Mapped[str] = mapped_column(String(255))
    actor_name: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(100), index=True)  # e.g. policy.created, event.status_changed
    resource_type: Mapped[str] = mapped_column(String(50), index=True)  # policy, event, risk, etc.
    resource_id: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    changes: Mapped[dict | None] = mapped_column(JSONB)  # before/after diff
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)  # additional context
