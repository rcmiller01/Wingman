"""Tests for dashboard query registry."""

from __future__ import annotations

import pytest

from homelab.dashboard.queries import (
    QueryReturnType,
    NamedQuery,
    get_query,
    list_queries,
    list_queries_by_return_type,
    get_query_descriptions,
)


class TestQueryReturnTypes:
    """Test query return types."""
    
    def test_all_return_types_exist(self):
        """All expected return types should be defined."""
        assert QueryReturnType.INTEGER
        assert QueryReturnType.FLOAT
        assert QueryReturnType.TABLE
        assert QueryReturnType.TIMESERIES
        assert QueryReturnType.LIST


class TestNamedQuery:
    """Test named query model."""
    
    def test_named_query_fields(self):
        """Named query should have expected fields."""
        assert hasattr(NamedQuery, '__annotations__')


class TestGetQuery:
    """Test query lookup."""
    
    def test_get_existing_query(self):
        """Existing query should be returned."""
        query = get_query("containers.active")
        
        assert query is not None
        assert query.id == "containers.active"
    
    def test_get_nonexistent_query(self):
        """Nonexistent query should return None."""
        query = get_query("nonexistent.query")
        
        assert query is None
    
    def test_get_query_has_sql(self):
        """Query should have SQL."""
        query = get_query("containers.total")
        
        assert query is not None
        assert query.sql is not None
        assert "SELECT" in query.sql.upper()


class TestListQueries:
    """Test query listing."""
    
    def test_list_queries_not_empty(self):
        """Query list should not be empty."""
        queries = list_queries()
        
        assert len(queries) > 0
    
    def test_list_queries_returns_strings(self):
        """Query list should return string IDs."""
        queries = list_queries()
        
        assert all(isinstance(q, str) for q in queries)


class TestListQueriesByReturnType:
    """Test filtering queries by return type."""
    
    def test_list_integer_queries(self):
        """Should find integer return type queries."""
        queries = list_queries_by_return_type(QueryReturnType.INTEGER)
        
        assert len(queries) > 0
        
        # Verify all returned are integers
        for qid in queries:
            query = get_query(qid)
            assert query.return_type == QueryReturnType.INTEGER


class TestQueryDescriptions:
    """Test query description retrieval."""
    
    def test_get_descriptions(self):
        """Should return descriptions for all queries."""
        descriptions = get_query_descriptions()
        
        assert len(descriptions) > 0
        assert all(isinstance(v, str) for v in descriptions.values())


class TestQueryCategories:
    """Test query organization by category."""
    
    def test_container_queries_exist(self):
        """Container queries should exist."""
        container_queries = [q for q in list_queries() if q.startswith("containers.")]
        
        assert len(container_queries) >= 1
    
    def test_incident_queries_exist(self):
        """Incident queries should exist."""
        incident_queries = [q for q in list_queries() if q.startswith("incidents.")]
        
        assert len(incident_queries) >= 1
