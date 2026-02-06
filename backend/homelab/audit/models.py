"""Audit logging models with tamper detection."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSON

from homelab.storage.models import Base, String, DateTime, Text


class AuditLog(Base):
    """Audit log entry with hash chain for tamper detection."""
    
    __tablename__ = "audit_logs"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    sequence: Mapped[int] = mapped_column(nullable=False, unique=True, index=True)
    
    # Event details
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)  # user, worker, system
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Action details
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Context
    metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Tamper detection (hash chain)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    __table_args__ = (
        Index("ix_audit_logs_sequence", "sequence"),
        Index("ix_audit_logs_event_type", "event_type"),
        Index("ix_audit_logs_actor_id", "actor_id"),
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_current_hash", "current_hash"),
        Index("ix_audit_logs_actor_type_id", "actor_type", "actor_id"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )
