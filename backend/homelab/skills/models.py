"""Skill models and enums."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class SkillCategory(str, Enum):
    """Categories of skills."""
    diagnostics = "diagnostics"
    remediation = "remediation"
    maintenance = "maintenance"
    monitoring = "monitoring"
    security = "security"


class SkillRisk(str, Enum):
    """Risk levels for skills, determining approval requirements."""
    low = "low"       # Tier 1: Auto-approve
    medium = "medium" # Tier 2: Requires human approval
    high = "high"     # Tier 3: Requires approval + judge audit


class SkillExecutionStatus(str, Enum):
    """Status of a skill execution."""
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"  # Explicitly rejected by approver
    executing = "executing"
    pending_audit = "pending_audit"  # For high-risk, waiting for judge
    completed = "completed"
    failed = "failed"
    retrying = "retrying"
    escalated = "escalated"  # Human intervention required


@dataclass
class SkillMeta:
    """Metadata describing a skill."""
    id: str
    name: str
    description: str
    category: SkillCategory
    risk: SkillRisk
    target_types: list[str]  # ["docker", "proxmox", "file"]
    required_params: list[str] = field(default_factory=list)
    optional_params: list[str] = field(default_factory=list)
    estimated_duration_seconds: int = 30
    requires_confirmation: bool = False  # Extra confirmation for destructive ops
    tags: list[str] = field(default_factory=list)


@dataclass
class Skill:
    """A complete skill definition with template."""
    meta: SkillMeta
    template: str  # Jinja2 template for rendering instructions/commands
    verification_template: str | None = None  # Template for verification step


@dataclass
class SkillExecution:
    """Record of a skill execution attempt."""
    id: str
    skill_id: str
    target: str
    parameters: dict[str, Any]
    status: SkillExecutionStatus
    created_at: datetime
    approved_at: datetime | None = None
    approved_by: str | None = None
    rejected_at: datetime | None = None
    rejected_by: str | None = None
    rejection_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # Execution results
    logs: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    
    # Audit fields
    audit_result: dict[str, Any] | None = None  # Judge's assessment
    retry_count: int = 0
    escalation_reason: str | None = None
    
    # Associated records
    incident_id: str | None = None
    action_history_id: str | None = None


# Pydantic models for API serialization

class SkillMetaResponse(BaseModel):
    """API response model for skill metadata."""
    id: str
    name: str
    description: str
    category: str  # .value of enum
    risk: str      # .value of enum
    target_types: list[str]
    required_params: list[str]
    optional_params: list[str]
    estimated_duration_seconds: int
    requires_confirmation: bool
    tags: list[str]
    
    class Config:
        from_attributes = True


class SkillListResponse(BaseModel):
    """API response for listing skills."""
    skills: list[SkillMetaResponse]
    total: int


class SkillRunRequest(BaseModel):
    """Request to run a skill."""
    target: str = Field(..., description="Target resource reference (e.g., docker://container-name)")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Skill parameters")
    incident_id: str | None = Field(None, description="Optional associated incident")
    skip_approval: bool = Field(False, description="Skip approval for low-risk skills only")


class SkillExecutionResponse(BaseModel):
    """API response for skill execution."""
    execution_id: str
    skill_id: str
    target: str
    status: str
    requires_approval: bool
    estimated_duration_seconds: int
    message: str
    
    class Config:
        from_attributes = True


class SkillApprovalRequest(BaseModel):
    """Request to approve a skill execution."""
    approved_by: str = Field(..., description="Username approving the execution")
    comment: str | None = Field(None, description="Optional approval comment")


class SkillRejectionRequest(BaseModel):
    """Request to reject a skill execution."""
    rejected_by: str = Field(..., description="Username rejecting the execution")
    reason: str | None = Field(None, description="Optional rejection reason")


class SkillSuggestionRequest(BaseModel):
    """Request for skill suggestions."""
    symptoms: list[str] = Field(..., description="List of symptoms or issues")
    target: str | None = Field(None, description="Optional target resource")
    max_results: int = Field(5, ge=1, le=20)


class SkillSuggestionResponse(BaseModel):
    """Suggested skill for a given situation."""
    skill_id: str
    name: str
    description: str
    category: str
    risk: str
    relevance_score: float
    reason: str
