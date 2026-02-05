"""Shared worker task/result envelope schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WorkerTaskEnvelope(BaseModel):
    """Control-plane to worker task payload."""

    task_id: str
    task_type: str
    idempotency_key: str
    worker_id: str
    site_name: str = "default"
    created_at: datetime
    timeout_seconds: int = 60
    payload: dict = Field(default_factory=dict)


class WorkerResultEnvelope(BaseModel):
    """Worker to control-plane result payload."""

    worker_id: str
    site_name: str = "default"
    timestamp: datetime
    payload_type: Literal["facts", "logs", "execution_result", "health"]
    task_id: str
    idempotency_key: str
    payload: dict = Field(default_factory=dict)


class WorkerClaimRequest(BaseModel):
    worker_id: str


class WorkerRegistrationRequest(BaseModel):
    worker_id: str
    site_name: str = "default"
    capabilities: dict = Field(default_factory=dict)


class WorkerHeartbeatRequest(BaseModel):
    worker_id: str
    site_name: str = "default"
    capabilities: dict = Field(default_factory=dict)


class WorkerEnqueueRequest(BaseModel):
    task_type: str
    worker_id: str
    idempotency_key: str
    payload: dict = Field(default_factory=dict)
    timeout_seconds: int = 60
    site_name: str = "default"
    max_attempts: int = 3
