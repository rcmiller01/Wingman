"""Configuration model for the standalone worker service."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


# Hardcoded safety constraints from v2 roadmap.
# These are NOT configurable — workers must never use cloud LLM.
ALLOW_CLOUD_LLM: bool = False
WORKER_MODE: str = "worker"


class WorkerSettings(BaseSettings):
    """Environment-driven settings for worker runtime."""

    model_config = SettingsConfigDict(
        env_prefix="WORKER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    worker_id: str = "worker-local-1"
    site: str = "default"
    control_plane_url: str = "http://localhost:8000"
    poll_interval_seconds: float = 2.0
    heartbeat_interval_seconds: float = 30.0
    shutdown_grace_seconds: float = 5.0

    # Offline buffer/replay — defaults aligned with ADR 0001
    offline_dir: str = "/data/offline"
    offline_max_files: int = 500
    offline_max_mb: int = 100
    offline_max_age_seconds: int = 86400  # 24 hours per ADR
    offline_replay_batch_size: int = 25
    offline_replay_interval_seconds: float = 0.05

    @property
    def allow_cloud_llm(self) -> bool:
        """Hardcoded — workers never use cloud LLM."""
        return ALLOW_CLOUD_LLM

    @property
    def mode(self) -> str:
        """Hardcoded — always 'worker'."""
        return WORKER_MODE


@lru_cache
def get_worker_settings() -> WorkerSettings:
    """Get cached worker settings."""

    return WorkerSettings()
