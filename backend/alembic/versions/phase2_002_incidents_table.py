"""phase2_incidents_table

Revision ID: phase2_002_incidents
Revises: phase2_001_facts
Create Date: 2026-02-05

Create incidents table for cross-site incident tracking and correlation.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'phase2_002_incidents'
down_revision = 'phase2_001_facts'
branch_labels = None
depends_on = None


def upgrade():
    # Create incidents table
    op.create_table(
        'incidents',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('incident_type', sa.String(100), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('site_name', sa.String(255), nullable=False),
        sa.Column('affected_sites', postgresql.JSON, nullable=False, server_default='[]'),
        sa.Column('correlation_group', sa.String(255), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('metadata', postgresql.JSON, nullable=False, server_default='{}'),
        sa.Column('detected_at', sa.DateTime, nullable=False),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
    )
    
    # Create indexes
    op.create_index('ix_incidents_incident_type', 'incidents', ['incident_type'])
    op.create_index('ix_incidents_site_name', 'incidents', ['site_name'])
    op.create_index('ix_incidents_detected_at', 'incidents', ['detected_at'])
    op.create_index('ix_incidents_site_severity', 'incidents', ['site_name', 'severity'])
    op.create_index('ix_incidents_correlation', 'incidents', ['correlation_group'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_incidents_correlation', 'incidents')
    op.drop_index('ix_incidents_site_severity', 'incidents')
    op.drop_index('ix_incidents_detected_at', 'incidents')
    op.drop_index('ix_incidents_site_name', 'incidents')
    op.drop_index('ix_incidents_incident_type', 'incidents')
    
    # Drop table
    op.drop_table('incidents')
