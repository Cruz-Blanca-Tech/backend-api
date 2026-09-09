"""crear tablas iniciales

Revision ID: ef0991b16c04
Revises: c28a843c9e29
Create Date: 2026-06-18 23:17:54.805151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ef0991b16c04'
down_revision: Union[str, Sequence[str], None] = 'c28a843c9e29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
