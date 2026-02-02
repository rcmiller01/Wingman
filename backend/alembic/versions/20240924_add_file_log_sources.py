"""Add file log sources table.

Revision ID: 20240924_add_file_log_sources
Revises: 
Create Date: 2024-09-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20240924_add_file_log_sources"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "file_log_sources",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("resource_ref", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("last_position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_file_log_sources_resource_ref",
        "file_log_sources",
        ["resource_ref"],
    )


def downgrade() -> None:
    op.drop_index("ix_file_log_sources_resource_ref", table_name="file_log_sources")
    op.drop_table("file_log_sources")
