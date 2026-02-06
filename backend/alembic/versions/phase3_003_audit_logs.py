"""phase3_audit_logs

Revision ID: phase3_003_audit_logs
Revises: phase3_002_service_accounts
Create Date: 2026-02-05

Create audit_logs table with hash chain for tamper detection.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'phase3_003_audit_logs'
down_revision = 'phase3_002_service_accounts'
branch_labels = None
depends_on = None


def upgrade():
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('sequence', sa.Integer, unique=True, nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('actor_type', sa.String(50), nullable=False),
        sa.Column('actor_id', sa.String(255), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('metadata', postgresql.JSON, nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('previous_hash', sa.String(64), nullable=True),
        sa.Column('current_hash', sa.String(64), nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
    )
    
    # Create indexes
    op.create_index('ix_audit_logs_sequence', 'audit_logs', ['sequence'])
    op.create_index('ix_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_current_hash', 'audit_logs', ['current_hash'])
    op.create_index('ix_audit_logs_actor_type_id', 'audit_logs', ['actor_type', 'actor_id'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_audit_logs_resource', 'audit_logs')
    op.drop_index('ix_audit_logs_actor_type_id', 'audit_logs')
    op.drop_index('ix_audit_logs_current_hash', 'audit_logs')
    op.drop_index('ix_audit_logs_timestamp', 'audit_logs')
    op.drop_index('ix_audit_logs_actor_id', 'audit_logs')
    op.drop_index('ix_audit_logs_event_type', 'audit_logs')
    op.drop_index('ix_audit_logs_sequence', 'audit_logs')
    
    # Drop table
    op.drop_table('audit_logs')
