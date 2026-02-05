"""Configuration model for the standalone worker service."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Phase-1 safety constraints from roadmap
    allow_cloud_llm: bool = False
    mode: str = "worker"


@lru_cache
def get_worker_settings() -> WorkerSettings:
    """Get cached worker settings."""

    return WorkerSettings()
