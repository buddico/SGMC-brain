"""Evidence pack models - CQC-ready evidence generation."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EvidencePackStatus(str, enum.Enum):
    GENERATING = "generating"
    READY = "ready"
    EXPORTED = "exported"
    FAILED = "failed"


class EvidencePack(Base):
    """A generated evidence pack for CQC or other third parties."""
    __tablename__ = "evidence_packs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    cqc_key_question: Mapped[str | None] = mapped_column(String(50))  # safe, effective, etc. or 'all'
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    status: Mapped[EvidencePackStatus] = mapped_column(Enum(EvidencePackStatus), default=EvidencePackStatus.GENERATING)
    file_path: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[dict | None] = mapped_column(JSONB)  # statistics and summary data
    generated_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["EvidenceItem"]] = relationship(back_populates="pack", cascade="all, delete-orphan")


class EvidenceItem(Base):
    """Individual items within an evidence pack."""
    __tablename__ = "evidence_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pack_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("evidence_packs.id", name="fk_evidence_items_pack_id"))
    item_type: Mapped[str] = mapped_column(String(50))  # event, policy, risk, check, alert
    item_id: Mapped[str] = mapped_column(String(100))  # UUID of the referenced entity
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text)
    evidence_data: Mapped[dict | None] = mapped_column(JSONB)
    cqc_quality_statement: Mapped[str | None] = mapped_column(String(200))
    sort_order: Mapped[int | None] = mapped_column()

    pack: Mapped[EvidencePack] = relationship(back_populates="items")
