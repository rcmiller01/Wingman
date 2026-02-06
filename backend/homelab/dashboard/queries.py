"""Named query registry for dashboard components."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QueryReturnType(str, Enum):
    """Return type of a named query."""
    
    INTEGER = "integer"
    FLOAT = "float"
    TABLE = "table"
    TIMESERIES = "timeseries"
    LIST = "list"
    TOPOLOGY = "topology"


class NamedQuery(BaseModel):
    """Named query definition."""
    
    id: str = Field(..., description="Unique query identifier")
    description: str = Field(..., description="Human-readable description")
    sql: str = Field(..., description="SQL query to execute")
    return_type: QueryReturnType = Field(..., description="Expected return type")
    parameters: list[str] = Field(default_factory=list, description="Allowed parameter names")


# Predefined named queries
NAMED_QUERIES: dict[str, NamedQuery] = {
    # ==================== Container Metrics ====================
    "containers.active": NamedQuery(
        id="containers.active",
        description="Count of active containers",
        sql="""
            SELECT COUNT(*) as value
            FROM facts 
            WHERE fact_type = 'container' 
            AND (data->>'status') = 'running'
        """,
        return_type=QueryReturnType.INTEGER,
    ),
    
    "containers.total": NamedQuery(
        id="containers.total",
        description="Total container count",
        sql="SELECT COUNT(*) as value FROM facts WHERE fact_type = 'container'",
        return_type=QueryReturnType.INTEGER,
    ),
    
    "containers.list": NamedQuery(
        id="containers.list",
        description="List all containers with status",
        sql="""
            SELECT 
                data->>'name' as name,
                data->>'status' as status,
                data->>'image' as image,
                created_at
            FROM facts 
            WHERE fact_type = 'container'
            ORDER BY created_at DESC
        """,
        return_type=QueryReturnType.TABLE,
    ),
    
    "containers.restarts_weekly": NamedQuery(
        id="containers.restarts_weekly",
        description="Container restarts over past week",
        sql="""
            SELECT 
                DATE(created_at) as timestamp,
                COUNT(*) as value
            FROM facts 
            WHERE fact_type = 'container_restart' 
            AND created_at > NOW() - INTERVAL '7 days'
            GROUP BY DATE(created_at)
            ORDER BY timestamp
        """,
        return_type=QueryReturnType.TIMESERIES,
    ),
    
    "containers.by_status": NamedQuery(
        id="containers.by_status",
        description="Containers grouped by status",
        sql="""
            SELECT 
                data->>'status' as name,
                COUNT(*) as value
            FROM facts 
            WHERE fact_type = 'container'
            GROUP BY data->>'status'
        """,
        return_type=QueryReturnType.TABLE,
    ),
    
    # ==================== Incidents ====================
    "incidents.recent_count": NamedQuery(
        id="incidents.recent_count",
        description="Incidents in last 24 hours",
        sql="""
            SELECT COUNT(*) as value
            FROM incidents 
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """,
        return_type=QueryReturnType.INTEGER,
    ),
    
    "incidents.by_severity": NamedQuery(
        id="incidents.by_severity",
        description="Incidents grouped by severity",
        sql="""
            SELECT 
                severity as name,
                COUNT(*) as value
            FROM incidents 
            GROUP BY severity
            ORDER BY 
                CASE severity 
                    WHEN 'critical' THEN 1 
                    WHEN 'high' THEN 2 
                    WHEN 'medium' THEN 3 
                    WHEN 'low' THEN 4 
                END
        """,
        return_type=QueryReturnType.TABLE,
    ),
    
    "incidents.recent_list": NamedQuery(
        id="incidents.recent_list",
        description="Recent incidents list",
        sql="""
            SELECT 
                id,
                title,
                severity,
                status,
                site_name,
                created_at as timestamp
            FROM incidents
            ORDER BY created_at DESC
            LIMIT 20
        """,
        return_type=QueryReturnType.TABLE,
    ),
    
    "incidents.weekly_trend": NamedQuery(
        id="incidents.weekly_trend",
        description="Incidents over past week",
        sql="""
            SELECT 
                DATE(created_at) as timestamp,
                COUNT(*) as value
            FROM incidents
            WHERE created_at > NOW() - INTERVAL '7 days'
            GROUP BY DATE(created_at)
            ORDER BY timestamp
        """,
        return_type=QueryReturnType.TIMESERIES,
    ),
    
    # ==================== Workers ====================
    "workers.active": NamedQuery(
        id="workers.active",
        description="Count of active workers",
        sql="""
            SELECT COUNT(*) as value
            FROM worker_nodes 
            WHERE status = 'online' 
            AND last_heartbeat > NOW() - INTERVAL '5 minutes'
        """,
        return_type=QueryReturnType.INTEGER,
    ),
    
    "workers.total": NamedQuery(
        id="workers.total",
        description="Total registered workers",
        sql="SELECT COUNT(*) as value FROM worker_nodes",
        return_type=QueryReturnType.INTEGER,
    ),
    
    "workers.by_site": NamedQuery(
        id="workers.by_site",
        description="Workers grouped by site",
        sql="""
            SELECT 
                site_name as name,
                COUNT(*) as value
            FROM worker_nodes 
            GROUP BY site_name
        """,
        return_type=QueryReturnType.TABLE,
    ),
    
    "workers.list": NamedQuery(
        id="workers.list",
        description="List all workers with status",
        sql="""
            SELECT 
                id,
                hostname,
                site_name,
                status,
                last_heartbeat
            FROM worker_nodes
            ORDER BY last_heartbeat DESC
        """,
        return_type=QueryReturnType.TABLE,
    ),
    
    # ==================== Tasks ====================
    "tasks.pending": NamedQuery(
        id="tasks.pending",
        description="Pending tasks count",
        sql="""
            SELECT COUNT(*) as value
            FROM worker_tasks 
            WHERE status = 'pending'
        """,
        return_type=QueryReturnType.INTEGER,
    ),
    
    "tasks.completed_today": NamedQuery(
        id="tasks.completed_today",
        description="Tasks completed today",
        sql="""
            SELECT COUNT(*) as value
            FROM worker_tasks 
            WHERE status = 'completed' 
            AND completed_at >= CURRENT_DATE
        """,
        return_type=QueryReturnType.INTEGER,
    ),
    
    "tasks.by_status": NamedQuery(
        id="tasks.by_status",
        description="Tasks grouped by status",
        sql="""
            SELECT 
                status as name,
                COUNT(*) as value
            FROM worker_tasks 
            GROUP BY status
        """,
        return_type=QueryReturnType.TABLE,
    ),
    
    "tasks.recent_completions": NamedQuery(
        id="tasks.recent_completions",
        description="Recently completed tasks",
        sql="""
            SELECT 
                id,
                plugin_id,
                action_type,
                status,
                completed_at as timestamp
            FROM worker_tasks
            WHERE status IN ('completed', 'failed')
            ORDER BY completed_at DESC
            LIMIT 20
        """,
        return_type=QueryReturnType.TABLE,
    ),
    
    # ==================== Facts ====================
    "facts.total": NamedQuery(
        id="facts.total",
        description="Total facts collected",
        sql="SELECT COUNT(*) as value FROM facts",
        return_type=QueryReturnType.INTEGER,
    ),
    
    "facts.by_type": NamedQuery(
        id="facts.by_type",
        description="Facts grouped by type",
        sql="""
            SELECT 
                fact_type as name,
                COUNT(*) as value
            FROM facts 
            GROUP BY fact_type
            ORDER BY value DESC
        """,
        return_type=QueryReturnType.TABLE,
    ),
    
    "facts.collection_trend": NamedQuery(
        id="facts.collection_trend",
        description="Facts collected over past week",
        sql="""
            SELECT 
                DATE(created_at) as timestamp,
                COUNT(*) as value
            FROM facts
            WHERE created_at > NOW() - INTERVAL '7 days'
            GROUP BY DATE(created_at)
            ORDER BY timestamp
        """,
        return_type=QueryReturnType.TIMESERIES,
    ),
    
    # ==================== Sites ====================
    "sites.active": NamedQuery(
        id="sites.active",
        description="Sites with recent activity",
        sql="""
            SELECT COUNT(DISTINCT site_name) as value
            FROM facts
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """,
        return_type=QueryReturnType.INTEGER,
    ),
    
    "sites.fact_counts": NamedQuery(
        id="sites.fact_counts",
        description="Facts per site",
        sql="""
            SELECT 
                site_name as name,
                COUNT(*) as value
            FROM facts
            GROUP BY site_name
            ORDER BY value DESC
        """,
        return_type=QueryReturnType.TABLE,
    ),
}


def get_query(query_id: str) -> NamedQuery | None:
    """Get named query by ID."""
    return NAMED_QUERIES.get(query_id)


def list_queries() -> list[str]:
    """List all available query IDs."""
    return list(NAMED_QUERIES.keys())


def list_queries_by_return_type(return_type: QueryReturnType) -> list[str]:
    """List queries by their return type."""
    return [
        q.id for q in NAMED_QUERIES.values()
        if q.return_type == return_type
    ]


def get_query_descriptions() -> dict[str, str]:
    """Get all query IDs with descriptions (for LLM prompt)."""
    return {q.id: q.description for q in NAMED_QUERIES.values()}
