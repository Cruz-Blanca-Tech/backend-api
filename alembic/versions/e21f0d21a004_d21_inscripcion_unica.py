"""D21: restricción única (beneficiary_id, activity_code) en beneficiary_enrollments

Revision ID: e21f0d21a004
Revises: d11e0d11a003
Create Date: 2026-11-08 00:00:00.000000

Antes de aplicarla en una base con datos, comprobar que no haya duplicados:

    SELECT beneficiary_id, activity_code, count(*)
      FROM beneficiary_enrollments
     GROUP BY 1, 2 HAVING count(*) > 1;

El 08/11/2026 la base de producción tenía 25 inscripciones y ningún duplicado.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "e21f0d21a004"
down_revision: Union[str, Sequence[str], None] = "d11e0d11a003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_enrollment_beneficiary_activity",
        "beneficiary_enrollments",
        ["beneficiary_id", "activity_code"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_enrollment_beneficiary_activity", "beneficiary_enrollments", type_="unique")
