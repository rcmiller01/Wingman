"""add hash chain fields to action_history

Revision ID: 20240925_add_audit_hash_chain
Revises: 20240924_add_file_log_sources
Create Date: 2024-09-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20240925_add_audit_hash_chain'
down_revision: Union[str, None] = '20240924_add_file_log_sources'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add hash chain fields for tamper-resistant audit trail."""
    # Add the new columns with defaults for existing rows
    op.add_column('action_history', sa.Column('prev_hash', sa.String(64), nullable=True))
    op.add_column('action_history', sa.Column('entry_hash', sa.String(64), nullable=True))
    op.add_column('action_history', sa.Column('sequence_num', sa.Integer(), nullable=True))
    
    # Create indexes for efficient chain traversal
    op.create_index('ix_action_history_entry_hash', 'action_history', ['entry_hash'])
    op.create_index('ix_action_history_sequence_num', 'action_history', ['sequence_num'])


def downgrade() -> None:
    """Remove hash chain fields."""
    op.drop_index('ix_action_history_sequence_num', table_name='action_history')
    op.drop_index('ix_action_history_entry_hash', table_name='action_history')
    op.drop_column('action_history', 'sequence_num')
    op.drop_column('action_history', 'entry_hash')
    op.drop_column('action_history', 'prev_hash')
