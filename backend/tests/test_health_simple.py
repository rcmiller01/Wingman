
import asyncio
import sys
import os
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

# Mock things BEFORE importing api.rag to avoid side effects
sys.modules["homelab.llm.providers"] = MagicMock()
sys.modules["homelab.rag.rag_indexer"] = MagicMock()
sys.modules["homelab.rag.log_summarizer"] = MagicMock()
sys.modules["homelab.config"] = MagicMock()
sys.modules["homelab.storage.database"] = MagicMock()

# Now import the function to test
# We need to manually import api.rag but since dependencies are mocked, it should be safe
# But we need to make sure 'homelab.api' exists as a package or mock it
# Better: just import from the file using importlib or rely on path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

# Create a dummy router so the decorator works
# Actually, if we mock 'homelab.api.rag' dependencies, we can import it.

# Let's try to verify the function object itself check_health
# by defining a similar one and seeing if it works, 
# trying to replicate exactly what rag.py does.

async def run_test():
    print("Importing check_health...")
    try:
        from homelab.api.rag import check_health
    except ImportError as e:
        print(f"ImportError: {e}")
        return

    print(f"check_health type: {type(check_health)}")
    
    # Mock get_settings and llm_manager inside the function scope if needed
    # But checking source, it calls:
    # llm_manager.is_embedding_blocked()
    # settings = get_settings()
    
    # We patched homelab.llm.providers.llm_manager above
    mock_llm_module = sys.modules["homelab.llm.providers"]
    mock_llm_module.llm_manager.is_embedding_blocked.return_value = True
    
    mock_config = sys.modules["homelab.config"]
    mock_config.get_settings.return_value.rag_retry_after_seconds = 123
    
    print("Calling check_health()...")
    res = await check_health()
    print(f"Result type: {type(res)}")
    print(f"Status: {res.status_code}")
    print(f"Body: {res.body}")

if __name__ == "__main__":
    asyncio.run(run_test())
