"""D11: columna raw_extracted_data en document_items

Revision ID: d11e0d11a003
Revises: c28d0d28a002
Create Date: 2026-11-08 00:00:00.000000

Guarda el JSON que devolvió Azure antes de la normalización del LLM, para saber
qué cambió la normalización. Los documentos procesados antes de la migración
quedan con NULL: ese dato ya no existe.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d11e0d11a003"
down_revision: Union[str, Sequence[str], None] = "c28d0d28a002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_items", sa.Column("raw_extracted_data", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_items", "raw_extracted_data")
