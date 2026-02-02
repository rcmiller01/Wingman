"""SQLAlchemy models for Homelab Copilot."""

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, Float, Boolean, JSON, ForeignKey, Enum, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from homelab.storage.database import Base


# ============================================================================
# Enums
# ============================================================================

class IncidentSeverity(str, PyEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(str, PyEnum):
    open = "open"
    investigating = "investigating"
    mitigated = "mitigated"
    resolved = "resolved"


class ActionTemplate(str, PyEnum):
    """MVP action templates - plugins can only recommend these."""
    restart_resource = "restart_resource"
    start_resource = "start_resource"
    stop_resource = "stop_resource"
    collect_diagnostics = "collect_diagnostics"
    verify_resource_health = "verify_resource_health"
    validate_paths = "validate_paths"
    validate_permissions = "validate_permissions"
    validate_dns_resolution = "validate_dns_resolution"
    validate_network_connectivity = "validate_network_connectivity"
    create_snapshot = "create_snapshot"
    rollback_to_snapshot = "rollback_to_snapshot"
    guided_ui_configuration = "guided_ui_configuration"


class ActionStatus(str, PyEnum):
    pending = "pending"
    approved = "approved"
    executing = "executing"
    completed = "completed"
    failed = "failed"


# ============================================================================
# Models
# ============================================================================

class Fact(Base):
    """Normalized observations from adapters."""
    __tablename__ = "facts"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    resource_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    fact_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # "docker", "proxmox", etc.
    
    __table_args__ = (
        Index("ix_facts_resource_time", "resource_ref", "timestamp"),
    )


class LogEntry(Base):
    """Raw log entries with 90-day retention metadata."""
    __tablename__ = "log_entries"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    resource_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    log_source: Mapped[str] = mapped_column(String(50), nullable=False)  # "stdout", "stderr", "file"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    retention_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # 90 days from creation
    
    __table_args__ = (
        Index("ix_log_entries_resource_time", "resource_ref", "timestamp"),
    )


class LogSummary(Base):
    """Compressed log summaries for RAG (12-month retention)."""
    __tablename__ = "log_summaries"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    resource_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False) # Renamed from summary to summary_text to match
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    log_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0) # Added log_count
    retention_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # 12 months from creation
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class Incident(Base):
    """Detected issues requiring investigation."""
    __tablename__ = "incidents"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    severity: Mapped[IncidentSeverity] = mapped_column(Enum(IncidentSeverity), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus), nullable=False, default=IncidentStatus.open)
    affected_resources: Mapped[list] = mapped_column(JSON, nullable=False)  # List of ResourceRefs
    symptoms: Mapped[list] = mapped_column(JSON, nullable=False)  # List of fact IDs / descriptions
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    narrative: Mapped["IncidentNarrative | None"] = relationship(back_populates="incident", uselist=False)
    actions: Mapped[list["ActionHistory"]] = relationship(back_populates="incident")


class IncidentNarrative(Base):
    """Long-form incident analysis for RAG indexing."""
    __tablename__ = "incident_narratives"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    incident_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("incidents.id", ondelete="CASCADE"), unique=True)
    
    time_range: Mapped[dict] = mapped_column(JSON, nullable=False)  # { start, end }
    root_cause_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0 - 1.0
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    resolution_steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    verification_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)  # resolved, mitigated, unresolved
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_incidents: Mapped[list | None] = mapped_column(JSON, nullable=True)
    agent_trace: Mapped[list | None] = mapped_column(JSON, nullable=True)  # Multi-agent conversation
    
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    incident: Mapped["Incident"] = relationship(back_populates="narrative")


class ActionHistory(Base):
    """Audit trail of approved and executed actions."""
    __tablename__ = "action_history"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    incident_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True)
    
    action_template: Mapped[ActionTemplate] = mapped_column(Enum(ActionTemplate), nullable=False)
    target_resource: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[ActionStatus] = mapped_column(Enum(ActionStatus), nullable=False, default=ActionStatus.pending)
    
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    incident: Mapped["Incident | None"] = relationship(back_populates="actions")


class AccessLog(Base):
    """API access audit trail."""
    __tablename__ = "access_logs"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    status_code: Mapped[int] = mapped_column(nullable=False)
    client_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
