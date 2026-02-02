import sys
import os
import asyncio
from fastapi.testclient import TestClient

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

# 1. Import Check
try:
    print("[Verify] Checking Imports...")
    from homelab.rag.rag_indexer import rag_indexer
    from homelab.rag.log_summarizer import log_summarizer
    from homelab.api.incidents import router as incidents_router
    # This proves the new import in incidents.py works
    print("[Verify] Imports Successful")
except ImportError as e:
    print(f"[Verify] Import Attempt Failed: {e}")
    sys.exit(1)
except NameError as e:
    print(f"[Verify] NameError (likely partial fix): {e}")
    sys.exit(1)

# 2. API Endpoint Check
from homelab.main import app

client = TestClient(app)

print("[Verify] Checking API Endpoints...")

# Check RAG prefix (should be /api/rag, not /rag)
response = client.post("/api/rag/search", json={"query": "test"})
if response.status_code == 404:
    print("[Verify] FAIL: /api/rag/search returned 404 (Did you fix the prefix?)")
else:
    print(f"[Verify] PASS: /api/rag/search returned {response.status_code} (Route exists)")

# Check Todos API (should exist)
response = client.get("/api/todos")
if response.status_code == 404:
    print("[Verify] FAIL: /api/todos returned 404 (Did you register the router?)")
else:
    print(f"[Verify] PASS: /api/todos returned {response.status_code}")

print("[Verify] Verification Complete")
