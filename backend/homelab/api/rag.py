"""RAG API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from homelab.storage import get_db
from homelab.rag import rag_indexer, summary_generator

router = APIRouter(prefix="/api/rag", tags=["rag"])


class SearchRequest(BaseModel):
    """Search request model."""
    query: str
    limit: int = 5


class SummaryRequest(BaseModel):
    """Summary generation request."""
    resource_ref: str
    date: str  # YYYY-MM-DD format


@router.post("/search/narratives")
async def search_narratives(request: SearchRequest):
    """Search incident narratives for similar content."""
    results = await rag_indexer.search_narratives(
        query=request.query,
        limit=request.limit,
    )
    
    return {
        "query": request.query,
        "count": len(results),
        "results": results,
    }


@router.post("/search/summaries")
async def search_summaries(request: SearchRequest):
    """Search log summaries for similar content."""
    results = await rag_indexer.search_summaries(
        query=request.query,
        limit=request.limit,
    )
    
    return {
        "query": request.query,
        "count": len(results),
        "results": results,
    }


@router.post("/generate/summary")
async def generate_summary(
    request: SummaryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a log summary for a specific resource and date."""
    try:
        date = datetime.strptime(request.date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    summary = await summary_generator.generate_daily_summary(
        db,
        resource_ref=request.resource_ref,
        date=date,
    )
    
    if not summary:
        return {
            "resource_ref": request.resource_ref,
            "date": request.date,
            "summary": None,
            "message": "No logs found for this date",
        }
    
    return {
        "resource_ref": request.resource_ref,
        "date": request.date,
        "summary": summary,
    }


@router.get("/context")
async def get_context_for_query(
    query: str = Query(..., min_length=3),
    limit: int = Query(5, le=20),
):
    """Get relevant context for a query (for LLM prompts)."""
    # Search both collections
    narratives = await rag_indexer.search_narratives(query, limit=limit)
    summaries = await rag_indexer.search_summaries(query, limit=limit)
    
    # Combine and sort by score
    all_results = []
    for n in narratives:
        all_results.append({
            "type": "narrative",
            "score": n["score"],
            "text": n["text"],
            "incident_id": n.get("incident_id"),
        })
    for s in summaries:
        all_results.append({
            "type": "summary",
            "score": s["score"],
            "text": s["text"],
            "resource_ref": s.get("resource_ref"),
        })
    
    # Sort by score descending
    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "query": query,
        "count": len(all_results),
        "context": all_results[:limit],
    }
