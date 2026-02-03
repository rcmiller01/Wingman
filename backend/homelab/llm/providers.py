"""LLM Provider Abstraction Layer.

Supports multiple LLM backends:
- Ollama (local)
- OpenRouter (cloud)
"""

import httpx
import logging
from abc import ABC, abstractmethod
from typing import Any
from enum import Enum

from homelab.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Available LLM providers."""
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"


class LLMFunction(str, Enum):
    """LLM function types for model selection."""
    CHAT = "chat"           # Narrative generation, analysis
    EMBEDDING = "embedding"  # Vector embeddings for RAG


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, model: str, **kwargs) -> str:
        """Generate text completion."""
        pass

    @abstractmethod
    async def embed(self, text: str, model: str) -> list[float] | None:
        """Generate embedding vector."""
        pass

    @abstractmethod
    async def list_models(self, function: LLMFunction | None = None) -> list[dict]:
        """List available models."""
        pass

    @abstractmethod
    def get_default_model(self, function: LLMFunction) -> str:
        """Get default model for a function."""
        pass


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider."""

    def __init__(self):
        self.base_url = settings.ollama_host
        self.default_chat_model = settings.ollama_model
        self.default_embedding_model = "nomic-embed-text"

    async def generate(self, prompt: str, model: str | None = None, **kwargs) -> str:
        """Generate text using Ollama."""
        model = model or self.default_chat_model
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        **kwargs,
                    },
                )
                response.raise_for_status()
                return response.json().get("response", "")
        except Exception as e:
            logger.error(f"[Ollama] Generate error: {e}")
            raise

    async def embed(self, text: str, model: str | None = None) -> list[float] | None:
        """Generate embedding using Ollama."""
        model = model or self.default_embedding_model
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": model,
                        "prompt": text[:4000],
                    },
                )
                response.raise_for_status()
                return response.json().get("embedding")
        except Exception as e:
            logger.error(f"[Ollama] Embedding error: {e}")
            return None

    async def list_models(self, function: LLMFunction | None = None) -> list[dict]:
        """List pulled Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                models = []
                for m in data.get("models", []):
                    name = m.get("name", "")
                    # Determine capabilities based on model name
                    is_embedding = "embed" in name.lower() or "nomic" in name.lower()
                    is_chat = not is_embedding

                    if function == LLMFunction.EMBEDDING and not is_embedding:
                        continue
                    if function == LLMFunction.CHAT and not is_chat:
                        continue

                    models.append({
                        "id": name,
                        "name": name,
                        "provider": "ollama",
                        "capabilities": {
                            "chat": is_chat,
                            "embedding": is_embedding,
                        },
                        "size": m.get("size"),
                        "modified_at": m.get("modified_at"),
                    })
                return models
        except Exception as e:
            logger.error(f"[Ollama] List models error: {e}")
            return []

    def get_default_model(self, function: LLMFunction) -> str:
        if function == LLMFunction.EMBEDDING:
            return self.default_embedding_model
        return self.default_chat_model


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter cloud LLM provider."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.default_chat_model = "anthropic/claude-3.5-sonnet"
        self.default_embedding_model = "openai/text-embedding-3-small"

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/homelab-copilot",
            "X-Title": "Homelab Copilot",
            "Content-Type": "application/json",
        }

    async def generate(self, prompt: str, model: str | None = None, **kwargs) -> str:
        """Generate text using OpenRouter."""
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")

        model = model or self.default_chat_model
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=self._get_headers(),
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        **kwargs,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"[OpenRouter] Generate error: {e}")
            raise

    async def embed(self, text: str, model: str | None = None) -> list[float] | None:
        """Generate embedding using OpenRouter (via OpenAI-compatible endpoint)."""
        if not self.api_key:
            logger.warning("[OpenRouter] API key not configured for embeddings")
            return None

        model = model or self.default_embedding_model
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/embeddings",
                    headers=self._get_headers(),
                    json={
                        "model": model,
                        "input": text[:8000],
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", [{}])[0].get("embedding")
        except Exception as e:
            logger.error(f"[OpenRouter] Embedding error: {e}")
            return None

    async def list_models(self, function: LLMFunction | None = None) -> list[dict]:
        """List available OpenRouter models."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers=self._get_headers() if self.api_key else {},
                )
                response.raise_for_status()
                data = response.json()

                models = []
                for m in data.get("data", []):
                    model_id = m.get("id", "")
                    context_length = m.get("context_length", 0)

                    # Determine capabilities
                    is_embedding = "embed" in model_id.lower()
                    is_chat = not is_embedding

                    if function == LLMFunction.EMBEDDING and not is_embedding:
                        continue
                    if function == LLMFunction.CHAT and not is_chat:
                        continue

                    models.append({
                        "id": model_id,
                        "name": m.get("name", model_id),
                        "provider": "openrouter",
                        "capabilities": {
                            "chat": is_chat,
                            "embedding": is_embedding,
                        },
                        "context_length": context_length,
                        "pricing": m.get("pricing", {}),
                    })

                # Sort by name for easier browsing
                models.sort(key=lambda x: x["name"].lower())
                return models

        except Exception as e:
            logger.error(f"[OpenRouter] List models error: {e}")
            return []

    def get_default_model(self, function: LLMFunction) -> str:
        if function == LLMFunction.EMBEDDING:
            return self.default_embedding_model
        return self.default_chat_model


class LLMManager:
    """Manages LLM providers and model selection."""

    def __init__(self):
        self._providers: dict[LLMProvider, BaseLLMProvider] = {}
        self._current_settings: dict[LLMFunction, dict] = {
            LLMFunction.CHAT: {
                "provider": LLMProvider.OLLAMA,
                "model": None,  # Use provider default
            },
            LLMFunction.EMBEDDING: {
                "provider": LLMProvider.OLLAMA,
                "model": None,  # Use provider default
            },
        }

    def _get_provider(self, provider: LLMProvider) -> BaseLLMProvider:
        """Get or create provider instance."""
        if provider not in self._providers:
            if provider == LLMProvider.OLLAMA:
                self._providers[provider] = OllamaProvider()
            elif provider == LLMProvider.OPENROUTER:
                self._providers[provider] = OpenRouterProvider()
            else:
                raise ValueError(f"Unknown provider: {provider}")
        return self._providers[provider]

    def get_settings(self) -> dict:
        """Get current LLM settings."""
        result = {}
        for func, config in self._current_settings.items():
            provider = self._get_provider(config["provider"])
            result[func.value] = {
                "provider": config["provider"].value,
                "model": config["model"] or provider.get_default_model(func),
            }
        return result

    def set_settings(self, function: LLMFunction, provider: LLMProvider, model: str | None = None):
        """Update LLM settings for a function."""
        self._current_settings[function] = {
            "provider": provider,
            "model": model,
        }

    async def generate(self, prompt: str, function: LLMFunction = LLMFunction.CHAT) -> str:
        """Generate text using configured provider."""
        config = self._current_settings[function]
        provider = self._get_provider(config["provider"])
        model = config["model"] or provider.get_default_model(function)
        return await provider.generate(prompt, model)

    async def embed(self, text: str) -> list[float] | None:
        """Generate embedding using configured provider."""
        config = self._current_settings[LLMFunction.EMBEDDING]
        provider = self._get_provider(config["provider"])
        model = config["model"] or provider.get_default_model(LLMFunction.EMBEDDING)
        return await provider.embed(text, model)

    async def list_models(self, provider: LLMProvider, function: LLMFunction | None = None) -> list[dict]:
        """List available models for a provider."""
        prov = self._get_provider(provider)
        return await prov.list_models(function)

    async def list_all_providers(self) -> list[dict]:
        """List all available providers with their status."""
        providers = []

        # Ollama
        ollama = self._get_provider(LLMProvider.OLLAMA)
        ollama_available = False
        try:
            models = await ollama.list_models()
            ollama_available = len(models) > 0
        except Exception:
            pass
        providers.append({
            "id": LLMProvider.OLLAMA.value,
            "name": "Ollama (Local)",
            "available": ollama_available,
            "configured": True,  # Always configured if Ollama host is set
        })

        # OpenRouter
        openrouter_configured = bool(settings.openrouter_api_key)
        providers.append({
            "id": LLMProvider.OPENROUTER.value,
            "name": "OpenRouter (Cloud)",
            "available": openrouter_configured,
            "configured": openrouter_configured,
        })

        return providers


# Singleton instance
llm_manager = LLMManager()
