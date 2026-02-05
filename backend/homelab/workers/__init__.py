"""Worker queue and protocol package."""

from homelab.workers.schemas import WorkerResultEnvelope, WorkerTaskEnvelope

__all__ = ["WorkerTaskEnvelope", "WorkerResultEnvelope"]
