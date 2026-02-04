"""Application configuration from environment variables."""

import os
from os.path import dirname, abspath, join
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
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
    proxmox_password: str | None = None
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
    secrets_path = Path("/run/secrets")

    def _read_secret(secret_name: str) -> str | None:
        secret_file = secrets_path / secret_name
        if secret_file.exists():
            return secret_file.read_text().strip()
        return None

    # Docker secrets: proxmox api token or individual fields
    if secrets_path.exists():
        if not s.proxmox_user:
            proxmox_user = _read_secret("proxmox_user")
            if proxmox_user:
                s.proxmox_user = proxmox_user
        if not s.proxmox_password:
            proxmox_password = _read_secret("proxmox_password")
            if proxmox_password:
                s.proxmox_password = proxmox_password
        if not s.proxmox_token_name:
            proxmox_token_name = _read_secret("proxmox_token_name")
            if proxmox_token_name:
                s.proxmox_token_name = proxmox_token_name
        if not s.proxmox_token_value:
            proxmox_token_value = _read_secret("proxmox_token_value")
            if proxmox_token_value:
                s.proxmox_token_value = proxmox_token_value

        proxmox_api_token = _read_secret("proxmox_api_token")
        if proxmox_api_token and not s.proxmox_token_value:
            # Supports "user@realm!tokenname:tokenvalue" or raw token value
            if ":" in proxmox_api_token and "!" in proxmox_api_token:
                token_id, token_value = proxmox_api_token.split(":", 1)
                s.proxmox_token_value = token_value.strip()
                if "!" in token_id:
                    user, token_name = token_id.split("!", 1)
                    if not s.proxmox_user:
                        s.proxmox_user = user.strip()
                    if not s.proxmox_token_name:
                        s.proxmox_token_name = token_name.strip()
            else:
                s.proxmox_token_value = proxmox_api_token.strip()

    # Mask password for security in logs
    safe_url = s.database_url.split("@")[-1] if "@" in s.database_url else s.database_url
    if s.debug:
        print(f"DEBUG: database_url (masked host)={safe_url}")
    return s
