from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import asyncio

from homelab.graph_service import GraphEdgeInput, GraphNodeInput, GraphReconciliationService
from homelab.storage.models import GraphEdge


def test_upsert_node_updates_existing_identity():
    async def run_test():
        service = GraphReconciliationService()
        existing = SimpleNamespace(attrs={"old": True}, last_seen_at=datetime.now(timezone.utc) - timedelta(hours=1))

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalars=lambda: MagicMock(first=lambda: existing))

        payload = GraphNodeInput(
            entity_type="container",
            entity_ref="docker://web",
            site_id="default",
            attrs={"state": "running"},
        )

        returned = await service.upsert_node(db, payload)

        assert returned is existing
        assert existing.attrs == {"state": "running"}
        assert existing.last_seen_at is not None
        db.add.assert_not_called()

    asyncio.run(run_test())


def test_upsert_edge_rehydrates_stale_edge():
    async def run_test():
        service = GraphReconciliationService()
        edge = GraphEdge(
            from_node_id="n1",
            to_node_id="n2",
            edge_type="depends_on",
            confidence=0.2,
            evidence_ref="facts:old",
            is_stale=True,
            stale_marked_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalars=lambda: MagicMock(first=lambda: edge))

        returned = await service.upsert_edge(
            db,
            GraphEdgeInput(
                from_node_id="n1",
                to_node_id="n2",
                edge_type="depends_on",
                confidence=0.98,
                evidence_ref="facts:new",
            ),
        )

        assert returned is edge
        assert edge.confidence == 0.98
        assert edge.evidence_ref == "facts:new"
        assert edge.is_stale is False
        assert edge.stale_marked_at is None

    asyncio.run(run_test())


def test_mark_stale_edges_marks_only_fresh_candidates():
    async def run_test():
        service = GraphReconciliationService()

        markable = GraphEdge(
            from_node_id="a",
            to_node_id="b",
            edge_type="serves",
            confidence=0.9,
            evidence_ref="facts:a",
            is_stale=False,
            last_seen_at=datetime.now(timezone.utc) - timedelta(days=3),
        )

        db = AsyncMock()
        db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: [markable]))

        changed = await service.mark_stale_edges(
            db,
            stale_before=datetime.now(timezone.utc) - timedelta(days=1),
        )

        assert changed == 1
        assert markable.is_stale is True
        assert markable.stale_marked_at is not None

    asyncio.run(run_test())
