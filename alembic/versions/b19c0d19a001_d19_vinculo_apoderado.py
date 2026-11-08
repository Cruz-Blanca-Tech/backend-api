"""D19: apoderado y contacto de emergencia por vínculo niño-adulto

Revision ID: b19c0d19a001
Revises: f3da3612c296
Create Date: 2026-11-08 00:00:00.000000

Agrega `is_guardian` e `is_emergency_contact` a `person_relationships` y
completa `relationship_type`, que nunca se escribía.

Relleno de datos existentes:
  - relationship_type: el rol del adulto (`adults.role`), en todos los vínculos.
  - marcas: solo cuando el adulto está vinculado a UN niño. Si está vinculado a
    varios, la marca del adulto es la del último expediente guardado y no se
    sabe de qué niño es: se deja NULL y la aplicación sigue usando la marca del
    adulto hasta que se vuelva a guardar ese niño.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b19c0d19a001"
down_revision: Union[str, Sequence[str], None] = "f3da3612c296"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("person_relationships", sa.Column("is_guardian", sa.Boolean(), nullable=True))
    op.add_column("person_relationships", sa.Column("is_emergency_contact", sa.Boolean(), nullable=True))
    op.execute(
        """
        UPDATE person_relationships pr
           SET relationship_type = a.role
          FROM adults a
         WHERE a.id = pr.to_person_id
           AND pr.relationship_type IS NULL
        """
    )
    op.execute(
        """
        UPDATE person_relationships pr
           SET is_guardian = a.is_guardian,
               is_emergency_contact = a.is_emergency_contact
          FROM adults a
         WHERE a.id = pr.to_person_id
           AND (SELECT count(*) FROM person_relationships x WHERE x.to_person_id = pr.to_person_id) = 1
        """
    )


def downgrade() -> None:
    op.drop_column("person_relationships", "is_emergency_contact")
    op.drop_column("person_relationships", "is_guardian")
