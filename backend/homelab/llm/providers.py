"""LLM Provider Abstraction Layer.

Supports multiple LLM backends:
- Ollama (local)
- OpenRouter (cloud)
"""

import httpx
import logging
import os
from abc import ABC, abstractmethod
from typing import Any
from enum import Enum

from homelab.config import get_settings
from homelab.llm.prompt_sanitizer import sanitize_prompt_for_cloud

settings = get_settings()
logger = logging.getLogger(__name__)

# Security toggle - set ALLOW_CLOUD_LLM=true to enable cloud providers
ALLOW_CLOUD_LLM = os.environ.get("ALLOW_CLOUD_LLM", "false").lower() == "true"

# Known embedding dimensions for common models
EMBEDDING_DIMENSIONS = {
    # Ollama models
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    "all-minilm": 384,
    # OpenAI models (via OpenRouter)
    "openai/text-embedding-3-small": 1536,
    "openai/text-embedding-3-large": 3072,
    "openai/text-embedding-ada-002": 1536,
}


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


class EmbeddingDimensionError(Exception):
    """Raised when embedding dimension would change and break existing collections."""
    pass


class CloudLLMDisabledError(Exception):
    """Raised when cloud LLM is attempted but not allowed."""
    pass


class EmbeddingBlockedError(Exception):
    """Raised when embedding operations are blocked due to inconsistent state."""
    pass


class LLMManager:
    """Manages LLM providers and model selection."""

    # Default embedding dimension (matches nomic-embed-text)
    DEFAULT_EMBEDDING_DIM = 768

    def __init__(self):
        import asyncio
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
        # Track the embedding dimension currently in use
        self._embedding_dimension: int = self.DEFAULT_EMBEDDING_DIM
        self._embedding_dimension_locked: bool = False  # Set True after first embedding
        self._embedding_inconsistent: bool = False  # True if Qdrant collections have mismatched dims
        self._embed_lock = asyncio.Lock()  # Prevent race on first embed

        # Warn if OpenRouter key is set but cloud is disabled
        if settings.openrouter_api_key and not ALLOW_CLOUD_LLM:
            logger.warning(
                "[LLMManager] OpenRouter API key is configured but ALLOW_CLOUD_LLM=false. "
                "Cloud provider will be ignored. Set ALLOW_CLOUD_LLM=true to enable."
            )

    def _get_provider(self, provider: LLMProvider) -> BaseLLMProvider:
        """Get or create provider instance."""
        # Secondary guard: refuse cloud provider if disabled (defense in depth)
        if provider == LLMProvider.OPENROUTER and not ALLOW_CLOUD_LLM:
            logger.error(
                "[LLMManager] Attempted to use OpenRouter but ALLOW_CLOUD_LLM=false. "
                "This should not happen - check for bypass in settings code."
            )
            raise CloudLLMDisabledError(
                "Cloud LLM providers are disabled. Set ALLOW_CLOUD_LLM=true to enable."
            )

        if provider not in self._providers:
            if provider == LLMProvider.OLLAMA:
                self._providers[provider] = OllamaProvider()
            elif provider == LLMProvider.OPENROUTER:
                self._providers[provider] = OpenRouterProvider()
            else:
                raise ValueError(f"Unknown provider: {provider}")
        return self._providers[provider]

    def is_cloud_allowed(self) -> bool:
        """Check if cloud LLM providers are allowed."""
        return ALLOW_CLOUD_LLM

    def get_embedding_dimension(self) -> int:
        """Get the current embedding dimension."""
        return self._embedding_dimension

    def prelock_from_qdrant(self, dimension: int) -> bool:
        """Pre-lock embedding dimension from existing Qdrant collections.

        Called during startup to sync with existing vector store state.
        Returns True if locked, False if already locked or invalid dimension.
        """
        if self._embedding_dimension_locked:
            if dimension != self._embedding_dimension:
                logger.warning(
                    f"[LLMManager] Qdrant dimension ({dimension}) differs from locked dimension "
                    f"({self._embedding_dimension}). This may cause issues."
                )
            return False

        if dimension <= 0:
            logger.warning(f"[LLMManager] Invalid Qdrant dimension: {dimension}")
            return False

        self._embedding_dimension = dimension
        self._embedding_dimension_locked = True
        logger.info(f"[LLMManager] Pre-locked embedding dimension from Qdrant: {dimension}")
        return True

    def set_inconsistent_state(self, inconsistent: bool) -> None:
        """Set the inconsistent state flag. When True, embedding operations are blocked."""
        self._embedding_inconsistent = inconsistent
        if inconsistent:
            logger.error(
                "[LLMManager] Embedding operations BLOCKED due to inconsistent Qdrant collection dimensions. "
                "Use /api/rag/collections/recreate to resolve."
            )

    def is_embedding_blocked(self) -> bool:
        """Check if embedding operations are blocked due to inconsistent state."""
        return self._embedding_inconsistent

    def get_model_embedding_dimension(self, model: str) -> int:
        """Get the expected embedding dimension for a model."""
        # Check known dimensions first
        if model in EMBEDDING_DIMENSIONS:
            return EMBEDDING_DIMENSIONS[model]
        # Default assumptions based on provider patterns
        if "nomic" in model.lower():
            return 768
        if "openai" in model.lower() or "text-embedding" in model.lower():
            return 1536
        # Unknown model - return current dimension (safe default)
        return self._embedding_dimension

    def get_settings(self) -> dict:
        """Get current LLM settings."""
        result = {}
        for func, config in self._current_settings.items():
            provider = self._get_provider(config["provider"])
            result[func.value] = {
                "provider": config["provider"].value,
                "model": config["model"] or provider.get_default_model(func),
            }
        result["embedding_dimension"] = self._embedding_dimension
        result["embedding_locked"] = self._embedding_dimension_locked
        result["embedding_blocked"] = self._embedding_inconsistent
        result["cloud_allowed"] = ALLOW_CLOUD_LLM
        return result

    def set_settings(
        self,
        function: LLMFunction,
        provider: LLMProvider,
        model: str | None = None,
        force_dimension_change: bool = False,
    ) -> dict:
        """Update LLM settings for a function.

        Returns dict with status info. Raises on validation errors.
        """
        # Security check for cloud providers
        if provider == LLMProvider.OPENROUTER and not ALLOW_CLOUD_LLM:
            raise CloudLLMDisabledError(
                "Cloud LLM providers are disabled. Set ALLOW_CLOUD_LLM=true to enable."
            )

        # Embedding dimension validation
        if function == LLMFunction.EMBEDDING and model:
            new_dim = self.get_model_embedding_dimension(model)
            if self._embedding_dimension_locked and new_dim != self._embedding_dimension:
                if not force_dimension_change:
                    raise EmbeddingDimensionError(
                        f"Cannot change embedding dimension from {self._embedding_dimension} to {new_dim}. "
                        f"This would break existing Qdrant collections. "
                        f"To proceed, you must recreate collections or use force_dimension_change=true."
                    )
                else:
                    logger.warning(
                        f"[LLMManager] Force changing embedding dimension from "
                        f"{self._embedding_dimension} to {new_dim}. Collections may need recreation."
                    )
                    self._embedding_dimension = new_dim

        self._current_settings[function] = {
            "provider": provider,
            "model": model,
        }

        return {
            "function": function.value,
            "provider": provider.value,
            "model": model,
            "embedding_dimension": self._embedding_dimension if function == LLMFunction.EMBEDDING else None,
        }

    async def generate(self, prompt: str, function: LLMFunction = LLMFunction.CHAT) -> str:
        """Generate text using configured provider."""
        config = self._current_settings[function]
        provider = self._get_provider(config["provider"])
        model = config["model"] or provider.get_default_model(function)
        prompt_to_send = prompt
        if config["provider"] == LLMProvider.OPENROUTER:
            prompt_to_send = sanitize_prompt_for_cloud(prompt)
            if prompt_to_send != prompt:
                logger.info("[LLMManager] Sanitized prompt for cloud provider to remove raw logs.")
        return await provider.generate(prompt_to_send, model)

    async def embed(self, text: str) -> list[float] | None:
        """Generate embedding using configured provider.

        Raises:
            EmbeddingBlockedError: If collections are in inconsistent state.
        """
        # Block if collections are in inconsistent state - fail loud, not silent
        if self._embedding_inconsistent:
            logger.error(
                "[LLMManager] Embedding request BLOCKED: Qdrant collections have inconsistent dimensions. "
                "Resolve via /api/rag/collections/recreate before indexing."
            )
            raise EmbeddingBlockedError(
                "Embedding operations are blocked due to inconsistent Qdrant collection dimensions. "
                "Use POST /api/rag/collections/recreate to resolve."
            )

        config = self._current_settings[LLMFunction.EMBEDDING]
        provider = self._get_provider(config["provider"])
        model = config["model"] or provider.get_default_model(LLMFunction.EMBEDDING)
        result = await provider.embed(text, model)

        # Lock dimension after first successful embedding (thread-safe)
        if result and not self._embedding_dimension_locked:
            async with self._embed_lock:
                # Double-check after acquiring lock
                if not self._embedding_dimension_locked:
                    actual_dim = len(result)
                    if actual_dim != self._embedding_dimension:
                        logger.info(f"[LLMManager] Detected embedding dimension: {actual_dim}")
                        self._embedding_dimension = actual_dim
                    self._embedding_dimension_locked = True
                    logger.info(f"[LLMManager] Embedding dimension locked at {self._embedding_dimension}")

        return result

    async def list_models(self, provider: LLMProvider, function: LLMFunction | None = None) -> list[dict]:
        """List available models for a provider."""
        prov = self._get_provider(provider)
        return await prov.list_models(function)

    async def list_all_providers(self) -> list[dict]:
        """List all available providers with their status."""
        providers = []

        # Ollama (always available as local option)
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
            "configured": True,
        })

        # OpenRouter (only show if cloud is allowed)
        if ALLOW_CLOUD_LLM:
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
