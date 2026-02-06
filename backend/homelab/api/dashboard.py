"""Dashboard API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from homelab.database import get_db
from homelab.dashboard.components import ComponentType
from homelab.dashboard.queries import list_queries, get_query_descriptions, get_query
from homelab.dashboard.schema import DashboardSpec, list_templates, get_template
from homelab.dashboard.generator import generate_dashboard, validate_dashboard_queries
from homelab.dashboard.executor import execute_query, execute_dashboard, QueryExecutionError


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# Request/Response models

class GenerateRequest(BaseModel):
    """Dashboard generation request."""
    prompt: str = Field(..., description="Natural language dashboard description")


class GenerateResponse(BaseModel):
    """Dashboard generation response."""
    spec: dict = Field(..., description="Generated dashboard specification")
    yaml: str = Field(..., description="YAML representation")
    validation_errors: list[str] = Field(default_factory=list)


class QueryInfo(BaseModel):
    """Query information."""
    id: str
    description: str
    return_type: str


class ComponentInfo(BaseModel):
    """Component information."""
    type: str
    description: str


class ExecuteRequest(BaseModel):
    """Query execution request."""
    query_id: str = Field(..., description="Named query ID")
    parameters: dict[str, Any] = Field(default_factory=dict)


# Endpoints

@router.post("/generate", response_model=GenerateResponse)
async def generate_dashboard_endpoint(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate dashboard from natural language description."""
    try:
        spec = await generate_dashboard(request.prompt)
        validation_errors = validate_dashboard_queries(spec)
        
        return GenerateResponse(
            spec=spec.model_dump(),
            yaml=spec.to_yaml(),
            validation_errors=validation_errors,
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")


@router.get("/queries")
async def list_available_queries() -> list[QueryInfo]:
    """List all available named queries."""
    queries = []
    
    for query_id in list_queries():
        query = get_query(query_id)
        if query:
            queries.append(QueryInfo(
                id=query.id,
                description=query.description,
                return_type=query.return_type.value,
            ))
    
    return queries


@router.get("/components")
async def list_available_components() -> list[ComponentInfo]:
    """List all available component types."""
    descriptions = {
        ComponentType.STAT_CARD: "Single metric display with optional trend",
        ComponentType.LINE_CHART: "Time series line chart",
        ComponentType.BAR_CHART: "Categorical bar chart",
        ComponentType.TABLE: "Tabular data display",
        ComponentType.TIMELINE: "Event timeline",
        ComponentType.TOPOLOGY: "Infrastructure topology graph",
        ComponentType.HEATMAP: "Activity heatmap",
        ComponentType.LIST: "Simple item list",
    }
    
    return [
        ComponentInfo(type=ct.value, description=desc)
        for ct, desc in descriptions.items()
    ]


@router.post("/execute")
async def execute_query_endpoint(
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Execute a named query."""
    try:
        result = await execute_query(
            db,
            request.query_id,
            request.parameters,
        )
        return {"query_id": request.query_id, "result": result}
    
    except QueryExecutionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates")
async def list_dashboard_templates() -> list[str]:
    """List available dashboard templates."""
    return list_templates()


@router.get("/templates/{template_id}")
async def get_dashboard_template(template_id: str):
    """Get a dashboard template by ID."""
    template = get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    
    return {
        "spec": template.model_dump(),
        "yaml": template.to_yaml(),
    }


@router.post("/render")
async def render_dashboard(
    spec: DashboardSpec,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Render a dashboard by executing all its queries.
    
    Returns the spec with query results populated.
    """
    try:
        results = await execute_dashboard(db, spec)
        
        return {
            "spec": spec.model_dump(),
            "data": results,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Render failed: {e}")
