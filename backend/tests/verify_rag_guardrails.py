
import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

# 1. Mock dependencies BEFORE importing application code to avoid side effects
sys.modules["homelab.llm.providers"] = MagicMock()
sys.modules["homelab.rag.rag_indexer"] = MagicMock()
sys.modules["homelab.rag.log_summarizer"] = MagicMock()
sys.modules["homelab.config"] = MagicMock()
sys.modules["homelab.storage.database"] = MagicMock()
sys.modules["homelab.rag.narrative_generator"] = MagicMock()
sys.modules["homelab.notifications.router"] = MagicMock()
sys.modules["homelab.control_plane.incident_detector"] = MagicMock()
sys.modules["homelab.storage"] = MagicMock()
sys.modules["homelab.storage.models"] = MagicMock()
sys.modules["homelab.adapters"] = MagicMock()
sys.modules["homelab.collectors"] = MagicMock()
# Mock entire packages safely
sys.modules["homelab.adapters.proxmox"] = MagicMock()
sys.modules["homelab.collectors.log_collector"] = MagicMock()
sys.modules["homelab.collectors.fact_collector"] = MagicMock()

# 2. Now import the functions to test
try:
    from homelab.api.rag import search_rag, SearchRequest, check_health
    from homelab.api.incidents import analyze_incident
    from homelab.llm.providers import EmbeddingBlockedError
    from starlette.exceptions import HTTPException
    from fastapi.responses import JSONResponse
except ImportError as e:
    print(f"ImportError during setup: {e}")
    sys.exit(1)

async def test_api_response_structure():
    print("Testing API Response structure...")
    
    # 1. Test Search
    print("- Testing Search API...")
    # We need to access the mocked rag_indexer that api.rag imported
    # Since we mocked sys.modules["homelab.rag.rag_indexer"], api.rag.rag_indexer is that mock
    from homelab.api.rag import rag_indexer as mock_indexer_instance
    
    # Reset side effects
    mock_indexer_instance.search_narratives.side_effect = EmbeddingBlockedError("Inconsistent state")
    
    # We also need to mock get_settings in config
    from homelab.config import get_settings as mock_get_settings
    mock_get_settings.return_value.rag_retry_after_seconds = 60

    try:
        await search_rag(SearchRequest(query="test"))
        print("FAIL: Search API did not raise HTTPException")
    except HTTPException as e:
        verify_503_exception(e, "Search API")

    # 2. Test Health
    print("- Testing Health API...")
    from homelab.llm.providers import llm_manager as mock_llm_manager
    mock_llm_manager.is_embedding_blocked.return_value = True
    
    response = await check_health()
    
    if not isinstance(response, JSONResponse):
         print(f"FAIL: Health API returned wrong type: {type(response)}")
    elif response.status_code != 503:
         print(f"FAIL: Health API returned {response.status_code}")
    else:
         import json
         body = json.loads(response.body)
         if body.get("status") != "blocked":
             print(f"FAIL: Health body mismatch: {body}")
         else:
             print("PASS: Health API (503 Blocked)")

    # 3. Test Analyze Incident
    print("- Testing Analyze Incident API...")
    from homelab.api.incidents import narrative_generator as mock_gen_instance
    mock_gen_instance.generate_narrative.side_effect = EmbeddingBlockedError("Blocked")
    
    try:
        await analyze_incident("inc-123", db=AsyncMock())
        print("FAIL: Analyze API did not raise HTTPException")
    except HTTPException as e:
        verify_503_exception(e, "Analyze Incident API")

def verify_503_exception(e, source):
    if e.status_code != 503:
        print(f"FAIL: {source} Wrong status code {e.status_code}")
        return
    
    if "Retry-After" not in e.headers or e.headers["Retry-After"] != "60":
        print(f"FAIL: {source} Wrong Retry-After header: {e.headers}")
        return
    
    detail = e.detail
    if detail.get("error") != "embedding_blocked" or "recovery" not in detail:
            print(f"FAIL: {source} Invalid JSON body: {detail}")
            return
            
    print(f"PASS: {source} verified")

if __name__ == "__main__":
    asyncio.run(test_api_response_structure())
