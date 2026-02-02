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
    
    # Database
    database_url: str = "postgresql+asyncpg://copilot:changeme@postgres:5432/homelab_copilot"
    
    # Qdrant
    qdrant_url: str = "http://qdrant:6333"
    
    # Ollama (local LLM)
    ollama_host: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:7b"
    
    # Cloud LLM (optional)
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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    s = Settings()
    # Mask password for security in logs
    safe_url = s.database_url.split("@")[-1] if "@" in s.database_url else s.database_url
    print(f"DEBUG: database_url (masked host)={safe_url}")
    return s
