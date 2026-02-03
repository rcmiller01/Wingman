"""Tests for embedding dimension safety and LLM provider guards.

These tests verify the critical safety mechanisms that prevent:
1. Embedding dimension mismatches breaking Qdrant collections
2. Race conditions on first embed
3. Cloud provider bypass when ALLOW_CLOUD_LLM=false
4. Destructive operations without proper guards
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os


class TestEmbeddingDimensionPrelock:
    """Test pre-locking dimension from Qdrant on startup."""

    def test_prelock_sets_dimension_and_locks(self):
        """Given mocked Qdrant size=768, manager locks=768 before embed."""
        # Import fresh to avoid singleton state
        with patch.dict(os.environ, {"ALLOW_CLOUD_LLM": "false"}):
            from homelab.llm.providers import LLMManager

            manager = LLMManager()
            assert not manager._embedding_dimension_locked

            # Prelock with Qdrant dimension
            result = manager.prelock_from_qdrant(768)

            assert result is True
            assert manager._embedding_dimension == 768
            assert manager._embedding_dimension_locked is True

    def test_prelock_rejects_if_already_locked(self):
        """Prelock returns False if already locked."""
        with patch.dict(os.environ, {"ALLOW_CLOUD_LLM": "false"}):
            from homelab.llm.providers import LLMManager

            manager = LLMManager()
            manager.prelock_from_qdrant(768)

            # Second prelock should fail
            result = manager.prelock_from_qdrant(1024)

            assert result is False
            assert manager._embedding_dimension == 768  # Unchanged

    def test_prelock_rejects_invalid_dimension(self):
        """Prelock rejects zero or negative dimensions."""
        with patch.dict(os.environ, {"ALLOW_CLOUD_LLM": "false"}):
            from homelab.llm.providers import LLMManager

            manager = LLMManager()

            assert manager.prelock_from_qdrant(0) is False
            assert manager.prelock_from_qdrant(-1) is False
            assert not manager._embedding_dimension_locked


class TestEmbeddingRaceSafety:
    """Test thread-safety of embedding dimension locking."""

    @pytest.mark.asyncio
    async def test_concurrent_embeds_lock_once(self):
        """Two concurrent embed calls lock once and don't disagree."""
        with patch.dict(os.environ, {"ALLOW_CLOUD_LLM": "false"}):
            from homelab.llm.providers import LLMManager, LLMProvider

            manager = LLMManager()

            # Mock the Ollama provider to return consistent embeddings
            mock_provider = MagicMock()
            mock_provider.embed = AsyncMock(return_value=[0.1] * 768)
            mock_provider.get_default_model = MagicMock(return_value="nomic-embed-text")
            manager._providers[LLMProvider.OLLAMA] = mock_provider

            # Run two embeds concurrently
            results = await asyncio.gather(
                manager.embed("text 1"),
                manager.embed("text 2"),
            )

            # Both should succeed
            assert results[0] is not None
            assert results[1] is not None

            # Dimension should be locked exactly once with correct value
            assert manager._embedding_dimension_locked is True
            assert manager._embedding_dimension == 768


class TestEmbeddingDimensionMismatchRejection:
    """Test that dimension changes are properly rejected."""

    def test_dimension_change_raises_error(self):
        """Locked=768, attempt set embedding model → 1536 raises EmbeddingDimensionError."""
        with patch.dict(os.environ, {"ALLOW_CLOUD_LLM": "false"}):
            from homelab.llm.providers import (
                LLMManager,
                LLMProvider,
                LLMFunction,
                EmbeddingDimensionError,
            )

            manager = LLMManager()
            manager.prelock_from_qdrant(768)

            # Attempt to switch to a model with different dimension
            with pytest.raises(EmbeddingDimensionError) as exc_info:
                manager.set_settings(
                    LLMFunction.EMBEDDING,
                    LLMProvider.OLLAMA,
                    model="mxbai-embed-large",  # 1024 dimensions
                )

            assert "768" in str(exc_info.value)
            assert "1024" in str(exc_info.value)

    def test_force_dimension_change_allowed(self):
        """Force flag allows dimension change with warning."""
        with patch.dict(os.environ, {"ALLOW_CLOUD_LLM": "false"}):
            from homelab.llm.providers import LLMManager, LLMProvider, LLMFunction

            manager = LLMManager()
            manager.prelock_from_qdrant(768)

            # Force change should succeed
            result = manager.set_settings(
                LLMFunction.EMBEDDING,
                LLMProvider.OLLAMA,
                model="mxbai-embed-large",
                force_dimension_change=True,
            )

            assert result["model"] == "mxbai-embed-large"
            assert manager._embedding_dimension == 1024


class TestCloudProviderGuard:
    """Test that cloud providers are properly blocked when disabled."""

    def test_cloud_provider_blocked_in_settings(self):
        """Cloud provider returns 403 equivalent when ALLOW_CLOUD_LLM=false."""
        with patch.dict(os.environ, {"ALLOW_CLOUD_LLM": "false"}):
            # Re-import to pick up env change
            import importlib
            import homelab.llm.providers as providers_module

            importlib.reload(providers_module)

            from homelab.llm.providers import (
                LLMManager,
                LLMProvider,
                LLMFunction,
                CloudLLMDisabledError,
            )

            manager = LLMManager()

            with pytest.raises(CloudLLMDisabledError):
                manager.set_settings(
                    LLMFunction.CHAT,
                    LLMProvider.OPENROUTER,
                    model="anthropic/claude-3.5-sonnet",
                )

    def test_cloud_provider_blocked_at_provider_level(self):
        """Defense in depth: _get_provider also blocks cloud when disabled."""
        with patch.dict(os.environ, {"ALLOW_CLOUD_LLM": "false"}):
            import importlib
            import homelab.llm.providers as providers_module

            importlib.reload(providers_module)

            from homelab.llm.providers import (
                LLMManager,
                LLMProvider,
                CloudLLMDisabledError,
            )

            manager = LLMManager()

            with pytest.raises(CloudLLMDisabledError):
                manager._get_provider(LLMProvider.OPENROUTER)


class TestDestructiveOperationGuards:
    """Test guards on destructive operations."""

    def test_recreate_blocked_without_env_flag(self):
        """Recreate collections fails without ALLOW_DESTRUCTIVE_ACTIONS=true."""
        with patch.dict(os.environ, {"ALLOW_DESTRUCTIVE_ACTIONS": "false"}):
            import importlib
            import homelab.rag.rag_indexer as indexer_module

            importlib.reload(indexer_module)

            # Mock QdrantClient to avoid real connections
            with patch("homelab.rag.rag_indexer.QdrantClient"):
                from homelab.rag.rag_indexer import RAGIndexer

                indexer = RAGIndexer()
                result = indexer.recreate_collections(768)

                assert result["success"] is False
                assert "ALLOW_DESTRUCTIVE_ACTIONS" in result["error"]


class TestInconsistentCollectionsBlocking:
    """Test that inconsistent collections block embedding operations."""

    @pytest.mark.asyncio
    async def test_embed_raises_when_inconsistent(self):
        """Embedding raises EmbeddingBlockedError when collections are inconsistent."""
        with patch.dict(os.environ, {"ALLOW_CLOUD_LLM": "false"}):
            from homelab.llm.providers import LLMManager, EmbeddingBlockedError

            manager = LLMManager()
            manager.set_inconsistent_state(True)

            with pytest.raises(EmbeddingBlockedError):
                await manager.embed("test text")

    def test_inconsistent_state_exposed_in_settings(self):
        """get_settings() includes embedding_blocked flag."""
        with patch.dict(os.environ, {"ALLOW_CLOUD_LLM": "false"}):
            from homelab.llm.providers import LLMManager

            manager = LLMManager()
            manager.set_inconsistent_state(True)

            settings = manager.get_settings()

            assert settings["embedding_blocked"] is True


class TestAPIResponses:
    """Test that API endpoints return proper status codes."""

    def test_embedding_blocked_error_is_importable(self):
        """EmbeddingBlockedError can be imported from providers module."""
        from homelab.llm.providers import EmbeddingBlockedError

        # Should be a proper exception class
        assert issubclass(EmbeddingBlockedError, Exception)

        # Should have a meaningful message when raised
        err = EmbeddingBlockedError("test message")
        assert "test message" in str(err)
