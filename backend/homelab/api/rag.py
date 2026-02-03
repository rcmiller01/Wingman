"""RAG API endpoints for debugging and manual control."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from homelab.storage.database import get_db
from homelab.rag.rag_indexer import rag_indexer
from homelab.rag.log_summarizer import log_summarizer
from homelab.llm.providers import llm_manager, EmbeddingBlockedError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

class SummarizeRequest(BaseModel):
    retention_days: int = 90

@router.post("/search")
async def search_rag(request: SearchRequest):
    """Search vector store for similar content."""
    try:
        narratives = await rag_indexer.search_narratives(request.query, limit=request.limit)
        summaries = await rag_indexer.search_summaries(request.query, limit=request.limit)
        return {
            "query": request.query,
            "results": {
                "narratives": narratives,
                "log_summaries": summaries,
            },
        }
    except EmbeddingBlockedError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
            headers={"Retry-After": "60"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize_logs")
async def trigger_log_summarization(
    request: SummarizeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger log summarization for expiring logs."""
    try:
        count = await log_summarizer.summarize_expiring_logs(db, retention_days=request.retention_days)
        return {"message": "Summarization complete", "summarized_logs_count": count}
    except EmbeddingBlockedError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
            headers={"Retry-After": "60"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections")
async def get_collection_info():
    """Get information about Qdrant collections including vector sizes."""
    info = rag_indexer.get_collection_info()
    settings = llm_manager.get_settings()
    return {
        **info,
        "target_dimension": llm_manager.get_embedding_dimension(),
        "dimension_locked": settings["embedding_locked"],
        "embedding_blocked": settings.get("embedding_blocked", False),
    }


class RecreateCollectionsRequest(BaseModel):
    new_dimension: int | None = None
    confirm: bool = False


@router.post("/collections/recreate")
async def recreate_collections(request: RecreateCollectionsRequest):
    """Recreate Qdrant collections with a new dimension.

    DESTRUCTIVE: This will delete all existing embeddings.
    Requires ALLOW_DESTRUCTIVE_ACTIONS=true environment variable.
    """
    if not request.confirm:
        return {
            "success": False,
            "error": "Must set confirm=true to proceed. This will DELETE all indexed data.",
            "current_info": rag_indexer.get_collection_info(),
        }

    # Audit log: capture state before destruction
    old_info = rag_indexer.get_collection_info()
    old_dim = llm_manager.get_embedding_dimension()

    # Use current LLM embedding dimension if not specified
    new_dim = request.new_dimension or old_dim

    logger.warning(
        f"[RAG] DESTRUCTIVE: Recreating collections. "
        f"Old dimension: {old_dim}, New dimension: {new_dim}. "
        f"Collections before: {old_info}"
    )

    result = rag_indexer.recreate_collections(new_dim)

    if result["success"]:
        # Reset LLM manager state for fresh start
        llm_manager._embedding_dimension = new_dim
        llm_manager._embedding_dimension_locked = False
        llm_manager.set_inconsistent_state(False)  # Clear blocked state

        logger.info(
            f"[RAG] Collections recreated successfully. "
            f"New dimension: {new_dim}. Embedding operations unblocked."
        )

    result["audit"] = {
        "timestamp": datetime.utcnow().isoformat(),
        "old_dimension": old_dim,
        "new_dimension": new_dim,
        "old_collections": old_info.get("collections", []),
    }

    return result
