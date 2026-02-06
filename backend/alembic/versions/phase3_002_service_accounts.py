"""phase3_service_accounts

Revision ID: phase3_002_service_accounts
Revises: phase3_001_users_sessions
Create Date: 2026-02-05

Create service_accounts table for API key authentication.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'phase3_002_service_accounts'
down_revision = 'phase3_001_users_sessions'
branch_labels = None
depends_on = None


def upgrade():
    # Create service_accounts table
    op.create_table(
        'service_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('api_key_hash', sa.String(64), unique=True, nullable=False),
        sa.Column('api_key_prefix', sa.String(8), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='operator'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('last_used', sa.DateTime, nullable=True),
        sa.Column('disabled', sa.Boolean, server_default='false'),
    )
    
    # Create index
    op.create_index('ix_service_accounts_api_key_hash', 'service_accounts', ['api_key_hash'])


def downgrade():
    # Drop index
    op.drop_index('ix_service_accounts_api_key_hash', 'service_accounts')
    
    # Drop table
    op.drop_table('service_accounts')
