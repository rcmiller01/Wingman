"""Application configuration from environment variables."""

import os
from os.path import dirname, abspath, join
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv

# Find .env in the root project directory
# Current file is backend/homelab/config.py
# Root is two levels up from backend/homelab/
base_dir = dirname(dirname(dirname(abspath(__file__))))
env_file_path = join(base_dir, ".env")

# Explicitly load .env
if os.path.exists(env_file_path):
    load_dotenv(env_file_path)

class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )
    
    # Server
    app_name: str = "Homelab Copilot"
    debug: bool = False
    environment: str = "development"  # development, staging, production
    
    # Auth
    auth_secret_key: str = "wingman-dev-secret-change-in-production"
    auth_enabled: bool = False  # Set to True to require authentication
    
    # Database
    database_url: str = "postgresql+asyncpg://copilot:changeme@postgres:5432/homelab_copilot"
    
    # Qdrant
    qdrant_url: str = "http://qdrant:6333"
    
    # Ollama (local LLM)
    ollama_host: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:7b"
    
    # Cloud LLM (optional)
    rag_retry_after_seconds: int = 60
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    openrouter_api_key: str | None = None
    
    # Proxmox (optional)
    proxmox_host: str | None = None
    proxmox_user: str | None = None
    proxmox_token_name: str | None = None
    proxmox_token_value: str | None = None
    proxmox_verify_ssl: bool = False
    
    # Notifications (optional)
    webhook_url: str | None = None
    webhook_secret: str | None = None

    # OpenTelemetry (optional)
    otel_endpoint: str | None = None
    otel_service_name: str = "homelab-copilot-backend"

    # Logging sinks (optional)
    ntfy_url: str | None = None
    ntfy_topic: str | None = None
    gotify_url: str | None = None
    gotify_token: str | None = None
    syslog_host: str | None = None
    syslog_port: int = 514

    # Alerting (optional)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None
    discord_webhook_url: str | None = None
    slack_webhook_url: str | None = None
    matrix_webhook_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    make_webhook_url: str | None = None
    plane_webhook_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    s = Settings()
    # Mask password for security in logs
    safe_url = s.database_url.split("@")[-1] if "@" in s.database_url else s.database_url
    if s.debug:
        print(f"DEBUG: database_url (masked host)={safe_url}")
    return s
