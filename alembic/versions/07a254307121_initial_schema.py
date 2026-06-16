"""initial_schema

Revision ID: 07a254307121
Revises: 
Create Date: 2026-06-05 00:09:36.960556

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07a254307121'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    No-op: esta migración inicial tenía un esquema incompatible (users.id como
    Integer mientras refresh_tokens.user_id era UUID). El esquema real lo crea
    la migración siguiente (c22af9d04987), que coincide con los modelos (UUID).
    """
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
