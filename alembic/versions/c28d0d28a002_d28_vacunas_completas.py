"""D28: campo has_complete_vaccines en la ficha médica del maestro

Revision ID: c28d0d28a002
Revises: b19c0d19a001
Create Date: 2026-11-08 00:00:00.000000

Antes se agregaba «COMPLETAS» a la lista de vacunas. Esta migración crea el
campo propio y marca como TRUE las fichas que ya tenían «COMPLETAS» en la lista
(la lista no se modifica, para no borrar datos).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c28d0d28a002"
down_revision: Union[str, Sequence[str], None] = "b19c0d19a001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("medical_records", sa.Column("has_complete_vaccines", sa.Boolean(), nullable=True))
    op.execute(
        """
        UPDATE medical_records
           SET has_complete_vaccines = TRUE
         WHERE EXISTS (
               SELECT 1 FROM json_array_elements_text(
                      CASE WHEN json_typeof(vaccines::json) = 'array' THEN vaccines::json ELSE '[]'::json END) v
                WHERE upper(v) = 'COMPLETAS')
        """
    )


def downgrade() -> None:
    op.drop_column("medical_records", "has_complete_vaccines")
