"""Graph storage and reconciliation services for dependency topology."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.storage.models import GraphEdge, GraphNode


@dataclass(frozen=True)
class GraphNodeInput:
    """Input payload for node upsert operations."""

    entity_type: str
    entity_ref: str
    site_id: str
    attrs: dict


@dataclass(frozen=True)
class GraphEdgeInput:
    """Input payload for edge upsert operations."""

    from_node_id: str
    to_node_id: str
    edge_type: str
    confidence: float
    evidence_ref: str


class GraphReconciliationService:
    """Handles idempotent graph upserts and stale-edge reconciliation."""

    async def upsert_node(self, db: AsyncSession, node: GraphNodeInput) -> GraphNode:
        now = datetime.now(timezone.utc)
        query = select(GraphNode).where(
            GraphNode.entity_type == node.entity_type,
            GraphNode.entity_ref == node.entity_ref,
            GraphNode.site_id == node.site_id,
        )
        result = await db.execute(query)
        existing = result.scalars().first()

        if existing:
            existing.attrs = node.attrs
            existing.last_seen_at = now
            return existing

        created = GraphNode(
            entity_type=node.entity_type,
            entity_ref=node.entity_ref,
            site_id=node.site_id,
            attrs=node.attrs,
            last_seen_at=now,
        )
        db.add(created)
        await db.flush()
        return created

    async def upsert_edge(self, db: AsyncSession, edge: GraphEdgeInput) -> GraphEdge:
        now = datetime.now(timezone.utc)
        query = select(GraphEdge).where(
            GraphEdge.from_node_id == edge.from_node_id,
            GraphEdge.to_node_id == edge.to_node_id,
            GraphEdge.edge_type == edge.edge_type,
        )
        result = await db.execute(query)
        existing = result.scalars().first()

        if existing:
            existing.confidence = edge.confidence
            existing.evidence_ref = edge.evidence_ref
            existing.last_seen_at = now
            existing.is_stale = False
            existing.stale_marked_at = None
            return existing

        created = GraphEdge(
            from_node_id=edge.from_node_id,
            to_node_id=edge.to_node_id,
            edge_type=edge.edge_type,
            confidence=edge.confidence,
            evidence_ref=edge.evidence_ref,
            last_seen_at=now,
        )
        db.add(created)
        await db.flush()
        return created

    async def mark_stale_edges(self, db: AsyncSession, stale_before: datetime) -> int:
        query = select(GraphEdge).where(
            GraphEdge.last_seen_at < stale_before,
            GraphEdge.is_stale.is_(False),
        )
        result = await db.execute(query)
        stale_candidates = result.scalars().all()

        now = datetime.now(timezone.utc)
        for edge in stale_candidates:
            edge.is_stale = True
            edge.stale_marked_at = now

        return len(stale_candidates)
