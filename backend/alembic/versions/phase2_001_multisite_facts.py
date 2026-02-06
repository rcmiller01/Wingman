"""phase2_multisite_fact_tracking

Revision ID: phase2_001_facts
Revises: 
Create Date: 2026-02-05

Add site_name, worker_id, and dedup_key to facts table for multi-site tracking and deduplication.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'phase2_001_facts'
down_revision = None  # TODO: Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to facts table
    op.add_column('facts', sa.Column('site_name', sa.String(255), nullable=False, server_default='default'))
    op.add_column('facts', sa.Column('worker_id', sa.String(255), nullable=True))
    op.add_column('facts', sa.Column('dedup_key', sa.String(512), nullable=True))
    
    # Create indexes
    op.create_index('ix_facts_site_name', 'facts', ['site_name'])
    op.create_index('ix_facts_worker_id', 'facts', ['worker_id'])
    op.create_index('ix_facts_site_type', 'facts', ['site_name', 'fact_type'])
    
    # Create unique index for dedup_key (only when not null)
    op.execute("""
        CREATE UNIQUE INDEX ix_facts_dedup 
        ON facts(dedup_key) 
        WHERE dedup_key IS NOT NULL
    """)


def downgrade():
    # Drop indexes
    op.drop_index('ix_facts_dedup', 'facts')
    op.drop_index('ix_facts_site_type', 'facts')
    op.drop_index('ix_facts_worker_id', 'facts')
    op.drop_index('ix_facts_site_name', 'facts')
    
    # Drop columns
    op.drop_column('facts', 'dedup_key')
    op.drop_column('facts', 'worker_id')
    op.drop_column('facts', 'site_name')
