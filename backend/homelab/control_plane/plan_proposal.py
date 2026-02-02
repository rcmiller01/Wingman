"""Plan Proposal models and interface."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from homelab.storage.models import ActionTemplate


class PlanStatus(str, Enum):
    """Status of a plan proposal."""
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    executing = "executing"
    completed = "completed"
    failed = "failed"


@dataclass
class PlanStep:
    """A single step in a plan."""
    order: int
    action: ActionTemplate
    target: str  # resource_ref
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    verification: str | None = None  # Description of verification
    status: str = "pending"
    result: dict[str, Any] | None = None
    executed_at: datetime | None = None


@dataclass
class PlanProposal:
    """A proposed remediation plan."""
    id: str
    incident_id: str | None
    title: str
    description: str
    steps: list[PlanStep]
    created_at: datetime
    status: PlanStatus = PlanStatus.pending
    approved_by: str | None = None
    approved_at: datetime | None = None
    executed_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "steps": [
                {
                    "order": s.order,
                    "action": s.action.value,
                    "target": s.target,
                    "params": s.params,
                    "description": s.description,
                    "verification": s.verification,
                    "status": s.status,
                    "result": s.result,
                    "executed_at": s.executed_at.isoformat() if s.executed_at else None,
                }
                for s in self.steps
            ],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }


class PlanStepSchema(BaseModel):
    """Schema for validating plan steps from LLM output."""

    model_config = ConfigDict(extra="forbid")

    order: int = Field(..., ge=1)
    action: ActionTemplate
    target: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    verification: str | None = None


class PlanProposalSchema(BaseModel):
    """Schema for validating plan proposals from LLM output."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1)
    description: str = Field(default="", max_length=4000)
    steps: list[PlanStepSchema] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_step_order(self) -> "PlanProposalSchema":
        orders = [step.order for step in self.steps]
        if len(orders) != len(set(orders)):
            raise ValueError("Step orders must be unique")
        if orders and orders != sorted(orders):
            raise ValueError("Step orders must be sorted ascending")
        return self


def proposal_payload_from_plan(plan: PlanProposal) -> dict[str, Any]:
    """Convert a PlanProposal into a schema payload for deterministic validation."""
    return {
        "title": plan.title,
        "description": plan.description,
        "steps": [
            {
                "order": step.order,
                "action": step.action,
                "target": step.target,
                "params": step.params,
                "description": step.description,
                "verification": step.verification,
            }
            for step in plan.steps
        ],
    }


def validate_plan_proposal(plan: PlanProposal) -> tuple[bool, list[str]]:
    """Validate a PlanProposal deterministically against the schema."""
    try:
        PlanProposalSchema.model_validate(proposal_payload_from_plan(plan), strict=True)
    except ValidationError as exc:
        errors = [f"{error['loc']}: {error['msg']}" for error in exc.errors()]
        return False, errors
    except ValueError as exc:
        return False, [str(exc)]
    return True, []


def plan_proposal_from_payload(payload: dict[str, Any], incident_id: str | None) -> PlanProposal:
    """Build a PlanProposal instance from a validated schema payload."""
    validated = PlanProposalSchema.model_validate(payload, strict=True)
    plan_steps = [
        PlanStep(
            order=step.order,
            action=step.action,
            target=step.target,
            params=step.params,
            description=step.description,
            verification=step.verification,
        )
        for step in validated.steps
    ]
    return PlanProposal(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        title=validated.title,
        description=validated.description,
        steps=plan_steps,
        created_at=datetime.utcnow(),
        status=PlanStatus.pending,
    )
