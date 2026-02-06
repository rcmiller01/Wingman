"""phase3_users_sessions

Revision ID: phase3_001_users_sessions
Revises: phase2_002_incidents
Create Date: 2026-02-05

Create users and sessions tables for OIDC authentication.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'phase3_001_users_sessions'
down_revision = 'phase2_002_incidents'
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('oidc_sub', sa.String(255), unique=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='viewer'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('last_login', sa.DateTime, nullable=True),
        sa.Column('disabled', sa.Boolean, server_default='false'),
    )
    
    # Create indexes for users
    op.create_index('ix_users_oidc_sub', 'users', ['oidc_sub'])
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('access_token_hash', sa.String(64), nullable=False),
        sa.Column('refresh_token_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('revoked_at', sa.DateTime, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    
    # Create indexes for sessions
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_sessions_access_token_hash', 'sessions', ['access_token_hash'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_sessions_access_token_hash', 'sessions')
    op.drop_index('ix_sessions_user_id', 'sessions')
    op.drop_index('ix_users_email', 'users')
    op.drop_index('ix_users_oidc_sub', 'users')
    
    # Drop tables
    op.drop_table('sessions')
    op.drop_table('users')
