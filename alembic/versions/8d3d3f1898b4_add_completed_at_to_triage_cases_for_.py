"""add completed_at to triage_cases for audit

Revision ID: 8d3d3f1898b4
Revises: f9e37bcf4ccd
Create Date: 2026-09-29 22:47:34.012660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8d3d3f1898b4'
down_revision: Union[str, Sequence[str], None] = 'f9e37bcf4ccd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('triage_cases', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('triage_cases', 'completed_at')