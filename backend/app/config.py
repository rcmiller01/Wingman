"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
