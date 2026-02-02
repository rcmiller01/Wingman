"""RAG API endpoints for debugging and manual control."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from homelab.storage.database import get_db
from homelab.rag.vector_store import vector_store
from homelab.rag.log_summarizer import log_summarizer

router = APIRouter(prefix="/rag", tags=["rag"])

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

class SummarizeRequest(BaseModel):
    retention_days: int = 90

@router.post("/search")
async def search_rag(request: SearchRequest):
    """Search vector store for similar content."""
    try:
        results = await vector_store.search_similar(request.query, limit=request.limit)
        return {"query": request.query, "results": results}
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
