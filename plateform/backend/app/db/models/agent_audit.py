from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin, utc_now


class AgentAuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_audit_events"

    public_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    agent_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_code: Mapped[str] = mapped_column(String(80), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(20), nullable=False)
    pipeline_stage: Mapped[str] = mapped_column(String(40), nullable=False)
    node_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    incident_public_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    detection_public_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    asset_public_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    external_cluster_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_device_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    reasoning_trace: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    safety_checks: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="mock_agent_data")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    run = relationship("AgentRun")
