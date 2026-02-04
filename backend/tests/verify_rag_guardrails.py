import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

from homelab.api import incidents as incidents_api
from homelab.api import rag as rag_api
from homelab.llm.providers import EmbeddingBlockedError


def _assert_embedding_blocked_exception(exc: HTTPException) -> None:
    assert exc.status_code == 503
    assert exc.headers.get("Retry-After") == "60"
    assert exc.detail.get("error") == "embedding_blocked"
    assert "recovery" in exc.detail


@pytest.mark.asyncio
async def test_search_rag_returns_503_when_blocked(monkeypatch):
    monkeypatch.setattr(
        rag_api.rag_indexer,
        "search_narratives",
        AsyncMock(side_effect=EmbeddingBlockedError("Inconsistent state")),
    )
    monkeypatch.setattr(
        rag_api,
        "get_settings",
        lambda: SimpleNamespace(rag_retry_after_seconds=60),
    )

    with pytest.raises(HTTPException) as exc_info:
        await rag_api.search_rag(rag_api.SearchRequest(query="test"))

    _assert_embedding_blocked_exception(exc_info.value)


@pytest.mark.asyncio
async def test_rag_health_blocked(monkeypatch):
    monkeypatch.setattr(rag_api.llm_manager, "is_embedding_blocked", MagicMock(return_value=True))
    monkeypatch.setattr(
        rag_api,
        "get_settings",
        lambda: SimpleNamespace(rag_retry_after_seconds=60),
    )

    response = await rag_api.check_health()

    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    assert response.headers.get("Retry-After") == "60"
    assert response.body is not None


@pytest.mark.asyncio
async def test_analyze_incident_returns_503_when_blocked(monkeypatch):
    incident = SimpleNamespace(id="inc-123")
    result = MagicMock()
    result.scalars.return_value.first.return_value = incident

    db = AsyncMock()
    db.execute.return_value = result

    monkeypatch.setattr(
        incidents_api.narrative_generator,
        "generate_narrative",
        AsyncMock(side_effect=EmbeddingBlockedError("Blocked")),
    )
    import homelab.config as config_module

    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: SimpleNamespace(rag_retry_after_seconds=60),
    )

    with pytest.raises(HTTPException) as exc_info:
        await incidents_api.analyze_incident("inc-123", db=db)

    _assert_embedding_blocked_exception(exc_info.value)
