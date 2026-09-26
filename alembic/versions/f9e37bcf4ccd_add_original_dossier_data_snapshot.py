"""add original_dossier_data snapshot

Revision ID: f9e37bcf4ccd
Revises: 904d90a6867c
Create Date: 2026-09-26 13:53:30.648181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f9e37bcf4ccd'
down_revision: Union[str, Sequence[str], None] = '904d90a6867c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Snapshot del "primer JSON" del expediente (dossier_data post-LLM, sin
    # intervención humana). Se persiste para comparar después contra la data
    # final que el usuario corrige/valida en triaje.
    op.add_column(
        'triage_cases',
        sa.Column('original_dossier_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Backfill: para los casos ya existentes, el mejor proxy del original es el
    # dossier_data actual (los pendientes conservan el post-LLM; los ya
    # corregidos parten de la copia corregida, documentado en el README/scratch).
    op.execute(
        "UPDATE triage_cases SET original_dossier_data = dossier_data "
        "WHERE original_dossier_data IS NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('triage_cases', 'original_dossier_data')
