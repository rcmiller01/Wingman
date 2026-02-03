import os
import sys

from fastapi.testclient import TestClient

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

from homelab.main import app


def test_imports_smoke():
    from homelab.rag.rag_indexer import rag_indexer
    from homelab.rag.log_summarizer import log_summarizer
    from homelab.api.incidents import router as incidents_router

    assert rag_indexer is not None
    assert log_summarizer is not None
    assert incidents_router is not None


def test_rag_search_route_exists():
    client = TestClient(app)
    response = client.post("/api/rag/search", json={"query": "test"})
    assert response.status_code != 404


def test_todos_route_exists():
    client = TestClient(app)
    response = client.get("/api/todos")
    assert response.status_code != 404
