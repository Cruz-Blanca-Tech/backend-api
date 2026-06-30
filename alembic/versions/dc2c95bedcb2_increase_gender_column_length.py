"""increase gender column length

Revision ID: dc2c95bedcb2
Revises: 37bfc05750a3
Create Date: 2026-06-30 00:01:03.975125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc2c95bedcb2'
down_revision: Union[str, Sequence[str], None] = '37bfc05750a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('persons', 'gender', type_=sa.String(10))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('persons', 'gender', type_=sa.String(1))
