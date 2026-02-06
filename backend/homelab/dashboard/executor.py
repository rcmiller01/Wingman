"""Execute named queries and return formatted results."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.dashboard.queries import get_query, QueryReturnType, NamedQuery


logger = logging.getLogger(__name__)


class QueryExecutionError(Exception):
    """Query execution failed."""
    pass


async def execute_query(
    db: AsyncSession,
    query_id: str,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a named query safely.
    
    Args:
        db: Database session
        query_id: Named query ID
        parameters: Optional query parameters
    
    Returns:
        Formatted result based on query return type
    
    Raises:
        QueryExecutionError: If query fails
    """
    query = get_query(query_id)
    if not query:
        raise QueryExecutionError(f"Unknown query: {query_id}")
    
    # Validate parameters
    params = parameters or {}
    for param in query.parameters:
        if param not in params:
            raise QueryExecutionError(f"Missing required parameter: {param}")
    
    try:
        result = await db.execute(text(query.sql), params)
        
        return format_result(result, query.return_type)
    
    except Exception as e:
        logger.error(f"Query execution failed: {query_id} - {e}")
        raise QueryExecutionError(f"Query execution failed: {e}")


def format_result(result: Any, return_type: QueryReturnType) -> dict[str, Any]:
    """Format query result based on return type."""
    
    if return_type == QueryReturnType.INTEGER:
        row = result.fetchone()
        value = row[0] if row else 0
        return {"value": int(value) if value is not None else 0}
    
    elif return_type == QueryReturnType.FLOAT:
        row = result.fetchone()
        value = row[0] if row else 0.0
        return {"value": float(value) if value is not None else 0.0}
    
    elif return_type == QueryReturnType.TABLE:
        rows = []
        columns = list(result.keys())
        
        for row in result.mappings():
            row_dict = {}
            for col in columns:
                val = row[col]
                # Convert datetime to ISO string
                if isinstance(val, datetime):
                    val = val.isoformat()
                row_dict[col] = val
            rows.append(row_dict)
        
        return {
            "columns": columns,
            "rows": rows,
            "total": len(rows),
        }
    
    elif return_type == QueryReturnType.TIMESERIES:
        data_points = []
        
        for row in result.mappings():
            row_dict = dict(row)
            # Convert timestamp
            if "timestamp" in row_dict and isinstance(row_dict["timestamp"], datetime):
                row_dict["timestamp"] = row_dict["timestamp"].isoformat()
            data_points.append(row_dict)
        
        return {
            "data": data_points,
            "total": len(data_points),
        }
    
    elif return_type == QueryReturnType.LIST:
        items = []
        
        for row in result.mappings():
            row_dict = dict(row)
            # Convert any datetime values
            for key, val in row_dict.items():
                if isinstance(val, datetime):
                    row_dict[key] = val.isoformat()
            items.append(row_dict)
        
        return {
            "items": items,
            "total": len(items),
        }
    
    elif return_type == QueryReturnType.TOPOLOGY:
        # Topology expects nodes and edges
        nodes = []
        edges = []
        
        for row in result.mappings():
            row_dict = dict(row)
            if "source" in row_dict and "target" in row_dict:
                edges.append({
                    "source": row_dict["source"],
                    "target": row_dict["target"],
                    "label": row_dict.get("label"),
                })
            else:
                nodes.append(row_dict)
        
        return {
            "nodes": nodes,
            "edges": edges,
        }
    
    else:
        raise QueryExecutionError(f"Unknown return type: {return_type}")


async def execute_dashboard(
    db: AsyncSession,
    spec: "DashboardSpec",
) -> dict[str, Any]:
    """Execute all queries in a dashboard spec.
    
    Returns dict mapping component queries to their results.
    """
    from homelab.dashboard.schema import DashboardSpec
    
    results = {}
    
    for section in spec.sections:
        for component in section.components:
            query_id = component.query
            
            if query_id not in results:
                try:
                    results[query_id] = await execute_query(db, query_id)
                except QueryExecutionError as e:
                    results[query_id] = {"error": str(e)}
    
    return results
