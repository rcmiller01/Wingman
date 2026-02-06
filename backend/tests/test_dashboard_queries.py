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
    NAMED_QUERIES,
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
        assert QueryReturnType.TOPOLOGY


class TestNamedQuery:
    """Test named query model."""
    
    def test_valid_named_query(self):
        """Valid named query should pass."""
        query = NamedQuery(
            id="test.query",
            description="A test query",
            sql="SELECT COUNT(*) FROM test",
            return_type=QueryReturnType.INTEGER,
        )
        
        assert query.id == "test.query"
        assert query.return_type == QueryReturnType.INTEGER
    
    def test_named_query_with_parameters(self):
        """Named query with parameters should pass."""
        query = NamedQuery(
            id="test.filtered",
            description="Filtered query",
            sql="SELECT * FROM test WHERE status = :status",
            return_type=QueryReturnType.TABLE,
            parameters=["status"],
        )
        
        assert "status" in query.parameters


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
    
    def test_list_queries_contains_expected(self):
        """Query list should contain expected queries."""
        queries = list_queries()
        
        expected = [
            "containers.active",
            "containers.total",
            "incidents.recent_count",
            "workers.active",
        ]
        
        for qid in expected:
            assert qid in queries


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
    
    def test_list_table_queries(self):
        """Should find table return type queries."""
        queries = list_queries_by_return_type(QueryReturnType.TABLE)
        
        assert len(queries) > 0
        
        for qid in queries:
            query = get_query(qid)
            assert query.return_type == QueryReturnType.TABLE
    
    def test_list_timeseries_queries(self):
        """Should find timeseries return type queries."""
        queries = list_queries_by_return_type(QueryReturnType.TIMESERIES)
        
        assert len(queries) > 0


class TestQueryDescriptions:
    """Test query description retrieval."""
    
    def test_get_descriptions(self):
        """Should return descriptions for all queries."""
        descriptions = get_query_descriptions()
        
        assert len(descriptions) > 0
        assert all(isinstance(v, str) for v in descriptions.values())
    
    def test_descriptions_match_queries(self):
        """Descriptions should match query IDs."""
        descriptions = get_query_descriptions()
        queries = list_queries()
        
        assert set(descriptions.keys()) == set(queries)


class TestQueryCategories:
    """Test query organization by category."""
    
    def test_container_queries_exist(self):
        """Container queries should exist."""
        container_queries = [q for q in list_queries() if q.startswith("containers.")]
        
        assert len(container_queries) >= 3
    
    def test_incident_queries_exist(self):
        """Incident queries should exist."""
        incident_queries = [q for q in list_queries() if q.startswith("incidents.")]
        
        assert len(incident_queries) >= 3
    
    def test_worker_queries_exist(self):
        """Worker queries should exist."""
        worker_queries = [q for q in list_queries() if q.startswith("workers.")]
        
        assert len(worker_queries) >= 2
    
    def test_task_queries_exist(self):
        """Task queries should exist."""
        task_queries = [q for q in list_queries() if q.startswith("tasks.")]
        
        assert len(task_queries) >= 2


class TestQuerySQL:
    """Test query SQL validity."""
    
    def test_all_queries_have_sql(self):
        """All queries should have SQL."""
        for qid in list_queries():
            query = get_query(qid)
            assert query.sql is not None
            assert len(query.sql) > 10
    
    def test_sql_is_select(self):
        """All queries should be SELECT statements."""
        for qid in list_queries():
            query = get_query(qid)
            # Allow SELECT or WITH (for CTEs)
            sql_upper = query.sql.strip().upper()
            assert sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")
