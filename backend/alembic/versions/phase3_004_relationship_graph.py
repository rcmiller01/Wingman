"""phase3_relationship_graph

Revision ID: phase3_004_relationship_graph
Revises: phase3_003_audit_logs
Create Date: 2026-02-06

Add graph_nodes and graph_edges tables for relationship topology.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "phase3_004_relationship_graph"
down_revision = "phase3_003_audit_logs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "graph_nodes",
        sa.Column("node_id", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_ref", sa.String(length=255), nullable=False),
        sa.Column("site_id", sa.String(length=128), nullable=False, server_default="default"),
        sa.Column("attrs", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("node_id"),
        sa.UniqueConstraint("entity_type", "entity_ref", "site_id", name="uq_graph_nodes_entity_identity"),
    )
    op.create_index("ix_graph_nodes_last_seen_at", "graph_nodes", ["last_seen_at"])
    op.create_index("ix_graph_nodes_site_entity", "graph_nodes", ["site_id", "entity_type"])

    op.create_table(
        "graph_edges",
        sa.Column("edge_id", sa.String(length=64), nullable=False),
        sa.Column("from_node_id", sa.String(length=64), nullable=False),
        sa.Column("to_node_id", sa.String(length=64), nullable=False),
        sa.Column("edge_type", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_ref", sa.String(length=255), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("stale_marked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["from_node_id"], ["graph_nodes.node_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_node_id"], ["graph_nodes.node_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("edge_id"),
        sa.UniqueConstraint("from_node_id", "to_node_id", "edge_type", name="uq_graph_edges_identity"),
    )
    op.create_index("ix_graph_edges_from_type", "graph_edges", ["from_node_id", "edge_type"])
    op.create_index("ix_graph_edges_to_type", "graph_edges", ["to_node_id", "edge_type"])
    op.create_index("ix_graph_edges_last_seen_at", "graph_edges", ["last_seen_at"])
    op.create_index("ix_graph_edges_is_stale", "graph_edges", ["is_stale"])


def downgrade():
    op.drop_index("ix_graph_edges_is_stale", table_name="graph_edges")
    op.drop_index("ix_graph_edges_last_seen_at", table_name="graph_edges")
    op.drop_index("ix_graph_edges_to_type", table_name="graph_edges")
    op.drop_index("ix_graph_edges_from_type", table_name="graph_edges")
    op.drop_table("graph_edges")

    op.drop_index("ix_graph_nodes_site_entity", table_name="graph_nodes")
    op.drop_index("ix_graph_nodes_last_seen_at", table_name="graph_nodes")
    op.drop_table("graph_nodes")
