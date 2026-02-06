"""SQLAlchemy models for Homelab Copilot."""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, Float, Boolean, JSON, ForeignKey, Enum, Index, Integer, UniqueConstraint
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
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
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
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class FileLogSource(Base):
    """Opt-in file log sources for tailing."""
    __tablename__ = "file_log_sources"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    resource_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    last_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Incident(Base):
    """Detected issues requiring investigation."""
    __tablename__ = "incidents"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    severity: Mapped[IncidentSeverity] = mapped_column(Enum(IncidentSeverity), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus), nullable=False, default=IncidentStatus.open)
    affected_resources: Mapped[list] = mapped_column(JSON, nullable=False)  # List of ResourceRefs
    symptoms: Mapped[list] = mapped_column(JSON, nullable=False)  # List of fact IDs / descriptions
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
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
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    incident: Mapped["Incident"] = relationship(back_populates="narrative")


class ActionHistory(Base):
    """
    Audit trail of approved and executed actions.
    
    IMMUTABILITY: This table is append-only. Entries should never be updated
    or deleted via the API. Each entry includes a hash chain linking to the
    previous entry, enabling tamper detection.
    
    Hash chain: entry_hash = SHA256(prev_hash + action_template + target + timestamp)
    
    Actor Attribution: Tracks who requested, approved, and executed each action
    for complete audit trail accountability.
    """
    __tablename__ = "action_history"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    incident_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True)
    
    action_template: Mapped[ActionTemplate] = mapped_column(Enum(ActionTemplate), nullable=False)
    target_resource: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[ActionStatus] = mapped_column(Enum(ActionStatus), nullable=False, default=ActionStatus.pending)
    
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Actor attribution for audit trail
    requested_by_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    requested_by_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    requested_by_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # First 16 chars of key hash
    approved_by_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    approved_by_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    approved_by_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    executed_by_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    executed_by_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Hash chain for tamper detection (append-only audit log)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA256 of previous entry
    entry_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # SHA256 of this entry
    sequence_num: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # Monotonic sequence
    
    # Relationships
    incident: Mapped["Incident | None"] = relationship(back_populates="actions")


class TodoStep(Base):
    """Pending plan steps awaiting approval."""
    __tablename__ = "todo_steps"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    incident_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True)

    order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_template: Mapped[ActionTemplate] = mapped_column(Enum(ActionTemplate), nullable=False)
    target_resource: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ActionStatus] = mapped_column(Enum(ActionStatus), nullable=False, default=ActionStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    action_history_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("action_history.id", ondelete="SET NULL"), nullable=True)

    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    incident: Mapped["Incident | None"] = relationship()
    action_history: Mapped["ActionHistory | None"] = relationship()


class AccessLog(Base):
    """API access audit trail."""
    __tablename__ = "access_logs"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    status_code: Mapped[int] = mapped_column(nullable=False)
    client_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)


class GraphNode(Base):
    """Stable topology node representing an observed entity."""

    __tablename__ = "graph_nodes"

    node_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    site_id: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    attrs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_ref", "site_id", name="uq_graph_nodes_entity_identity"),
        Index("ix_graph_nodes_site_entity", "site_id", "entity_type"),
    )


class GraphEdge(Base):
    """Directed relationship between topology nodes with provenance."""

    __tablename__ = "graph_edges"

    edge_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    from_node_id: Mapped[str] = mapped_column(String(64), ForeignKey("graph_nodes.node_id", ondelete="CASCADE"), nullable=False)
    to_node_id: Mapped[str] = mapped_column(String(64), ForeignKey("graph_nodes.node_id", ondelete="CASCADE"), nullable=False)
    edge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    stale_marked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("from_node_id", "to_node_id", "edge_type", name="uq_graph_edges_identity"),
        Index("ix_graph_edges_from_type", "from_node_id", "edge_type"),
        Index("ix_graph_edges_to_type", "to_node_id", "edge_type"),
    )


class WorkerTaskStatus(str, PyEnum):
    queued = "queued"
    claimed = "claimed"
    running = "running"
    done = "done"
    failed = "failed"
    dead_letter = "dead_letter"


class WorkerStatus(str, PyEnum):
    online = "online"
    offline = "offline"
    degraded = "degraded"


class WorkerTask(Base):
    """Persistent worker task queue entry for pg_notify dispatch."""

    __tablename__ = "worker_tasks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    worker_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    site_name: Mapped[str] = mapped_column(String(255), nullable=False, default="default")
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    status: Mapped[WorkerTaskStatus] = mapped_column(Enum(WorkerTaskStatus), nullable=False, default=WorkerTaskStatus.queued, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    __table_args__ = (
        Index("ix_worker_tasks_status_retry", "status", "next_retry_at"),
    )


class WorkerNode(Base):
    """Worker registration and heartbeat state."""

    __tablename__ = "worker_nodes"

    worker_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    site_name: Mapped[str] = mapped_column(String(255), nullable=False, default="default")
    capabilities: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[WorkerStatus] = mapped_column(Enum(WorkerStatus), nullable=False, default=WorkerStatus.online, index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class WorkerResult(Base):
    """Worker result envelope persistence for idempotent reconciliation."""

    __tablename__ = "worker_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    worker_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    payload_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("ix_worker_results_task_idem", "task_id", "idempotency_key", unique=True),
    )
