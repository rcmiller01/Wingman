"""Health check API endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.storage import get_db
from homelab.rag.rag_indexer import rag_indexer
from homelab.runtime import get_execution_mode, get_safety_policy
from homelab.runtime.mode import get_mode_description
from homelab.policy import get_lab_safety_status

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check."""
    db_status = "unknown"
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
        db_ok = True
    except Exception as e:
        db_status = f"error: {str(e)}"

    qdrant_status = "unknown"
    qdrant_ok = False
    qdrant_info = {}
    try:
        qdrant_info = rag_indexer.get_collection_info()
        if qdrant_info.get("error"):
            qdrant_status = f"error: {qdrant_info['error']}"
        else:
            qdrant_status = "connected"
            qdrant_ok = True
    except Exception as e:
        qdrant_status = f"error: {str(e)}"

    mode = get_execution_mode()
    safety_policy = get_safety_policy()
    lab_status = get_lab_safety_status()

    safety_loaded = safety_policy is not None
    overall_ok = db_ok and qdrant_ok and safety_loaded
    status = "healthy" if overall_ok else "degraded"

    payload = {
        "status": status,
        "service": "homelab-copilot",
        "database": db_status,
        "qdrant": qdrant_status,
        "qdrant_collections": qdrant_info.get("collections", []),
        "execution_mode": {
            "value": mode.value,
            "description": get_mode_description(),
        },
        "safety_policy": {
            "loaded": safety_loaded,
            "name": type(safety_policy).__name__ if safety_policy else None,
            "lab_status": lab_status.to_dict(),
        },
    }

    return JSONResponse(status_code=200 if overall_ok else 503, content=payload)


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check including database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    qdrant_status = "unknown"
    try:
        qdrant_info = rag_indexer.get_collection_info()
        qdrant_status = "connected" if not qdrant_info.get("error") else f"error: {qdrant_info['error']}"
    except Exception as e:
        qdrant_status = f"error: {str(e)}"

    ready = db_status == "connected" and qdrant_status == "connected"
    return {
        "status": "ready" if ready else "degraded",
        "database": db_status,
        "qdrant": qdrant_status,
    }


@router.get("/metrics")
async def metrics():
    """Minimal Prometheus-style metrics endpoint."""
    return PlainTextResponse("wingman_up 1\n")
