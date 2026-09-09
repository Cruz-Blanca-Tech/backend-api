"""add_failed_events_and_triage_sync_status

Revision ID: 904d90a6867c
Revises: bbac9862d10c
Create Date: 2026-09-08 20:35:23.663622

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '904d90a6867c'
down_revision: Union[str, Sequence[str], None] = 'bbac9862d10c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Crear tabla failed_events
    op.create_table(
        'failed_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_name', sa.String(length=100), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('handler_name', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('error_message', sa.String(length=1000), nullable=False),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='FAILED', nullable=False),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_failed_events_status', 'failed_events', ['status'])
    op.create_index('ix_failed_events_aggregate_id', 'failed_events', ['aggregate_id'])

    # 2. Agregar columnas a triage_cases
    op.add_column('triage_cases', sa.Column('sync_status', sa.String(length=50), server_default='PENDING', nullable=True))
    op.add_column('triage_cases', sa.Column('sync_error', sa.String(length=1000), nullable=True))
    op.create_index('ix_triage_cases_sync_status', 'triage_cases', ['sync_status'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_triage_cases_sync_status', table_name='triage_cases')
    op.drop_column('triage_cases', 'sync_error')
    op.drop_column('triage_cases', 'sync_status')

    op.drop_index('ix_failed_events_aggregate_id', table_name='failed_events')
    op.drop_index('ix_failed_events_status', table_name='failed_events')
    op.drop_table('failed_events')
