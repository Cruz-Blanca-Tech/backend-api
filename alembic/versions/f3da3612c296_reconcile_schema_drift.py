"""reconcile schema drift: schools, activities, extraction_batches, adults

Revision ID: f3da3612c296
Revises: 8d3d3f1898b4
Create Date: 2026-09-30 01:05:00.000000

Este esquema se fue construyendo a lo largo de varias sesiones yparts del
código llegaron a la base de datos sin su migración correspondiente. El síntoma
visible era un 500 genérico ("Error interno del sistema") al iniciar la
extracción de un lote: `ExtractionBatchModel` declara `failure_reason`, la
consulta de `BatchRepository.save()` lo selecciona siempre, y la columna no
existía.

Reúne TODO el drift en una sola revisión para que `alembic upgrade head` sobre
una base vacía produzca un esquema completo, y para eliminar la necesidad de los
scripts sueltos que se corrían a mano tras cada reset:

  - schools                              (tabla completa, faltaba entera)
  - activities.activity_type             (la usa `Activity` y el motor EDUCA)
  - activities.start_date / end_date
  - extraction_batches.failure_reason    (causa del 500 al iniciar extracción)
  - adults.is_guardian                   (lo escribe el mapeo del expediente)
  - person_relationships                 (tabla asociativa, faltaba entera)

Es IDEMPOTENTE a propósito: la base de desarrollo ya tiene `schools` y las
columnas de `activities` creadas a mano, y esta migración tiene que poder
aplicarse encima sin reventar. Por eso todo se guarda con "si no existe".
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f3da3612c296"
down_revision: Union[str, Sequence[str], None] = "8d3d3f1898b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table: str) -> bool:
    return (
        conn.execute(
            sa.text("SELECT to_regclass(:name)"), {"name": f"public.{table}"}
        ).scalar()
        is not None
    )


def _column_exists(conn, table: str, column: str) -> bool:
    if not _table_exists(conn, table):
        return False
    return (
        conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
            ),
            {"t": table, "c": column},
        ).scalar()
        is not None
    )


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # schools: la usa el maestro de colegios (MDM) y no existia en ninguna
    # migracion. `create_schools_table.py` la creaba a mano en la base local.
    # ------------------------------------------------------------------
    if not _table_exists(conn, "schools"):
        op.create_table(
            "schools",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("location", sa.String(length=255), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column(
                "is_active",
                sa.Boolean(),
                server_default=sa.text("true"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index("ix_schools_name", "schools", ["name"], unique=True)
        op.create_index("ix_schools_is_active", "schools", ["is_active"])

    # ------------------------------------------------------------------
    # activities: `Activity` es un dataclass que exige activity_type,
    # start_date y end_date. Sin estas columnas el mapper falla al hidratar.
    # ------------------------------------------------------------------
    if not _column_exists(conn, "activities", "activity_type"):
        op.add_column(
            "activities",
            sa.Column(
                "activity_type",
                sa.String(length=50),
                server_default="UNKNOWN",
                nullable=False,
            ),
        )
    if not _column_exists(conn, "activities", "start_date"):
        op.add_column(
            "activities", sa.Column("start_date", sa.Date(), nullable=True)
        )
    if not _column_exists(conn, "activities", "end_date"):
        op.add_column("activities", sa.Column("end_date", sa.Date(), nullable=True))

    # ------------------------------------------------------------------
    # extraction_batches.failure_reason: el motivo por el que un lote quedo
    # FAILED lo escribe la orquestacion y lo expone el listado de lotes.
    # ------------------------------------------------------------------
    if not _column_exists(conn, "extraction_batches", "failure_reason"):
        op.add_column(
            "extraction_batches",
            sa.Column("failure_reason", sa.String(length=1000), nullable=True),
        )

    # ------------------------------------------------------------------
    # adults.is_guardian: distingue al apoderado del simple contacto de
    # emergencia.
    # ------------------------------------------------------------------
    if not _column_exists(conn, "adults", "is_guardian"):
        op.add_column(
            "adults",
            sa.Column(
                "is_guardian",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
        )

    # ------------------------------------------------------------------
    # person_relationships: tabla asociativa N:M entre personas. La usan
    # `adults.beneficiaries` y `beneficiaries.relatives`; sin ella, cargar un
    # beneficiario con familiares revienta al resolver la relationship.
    # ------------------------------------------------------------------
    if not _table_exists(conn, "person_relationships"):
        op.create_table(
            "person_relationships",
            sa.Column("from_person_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("to_person_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("relationship_type", sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(["from_person_id"], ["persons.id"]),
            sa.ForeignKeyConstraint(["to_person_id"], ["persons.id"]),
            sa.PrimaryKeyConstraint("from_person_id", "to_person_id"),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _table_exists(conn, "person_relationships"):
        op.drop_table("person_relationships")
    if _column_exists(conn, "adults", "is_guardian"):
        op.drop_column("adults", "is_guardian")
    if _column_exists(conn, "extraction_batches", "failure_reason"):
        op.drop_column("extraction_batches", "failure_reason")
    if _column_exists(conn, "activities", "end_date"):
        op.drop_column("activities", "end_date")
    if _column_exists(conn, "activities", "start_date"):
        op.drop_column("activities", "start_date")
    if _column_exists(conn, "activities", "activity_type"):
        op.drop_column("activities", "activity_type")
    if _table_exists(conn, "schools"):
        op.drop_index("ix_schools_is_active", table_name="schools")
        op.drop_index("ix_schools_name", table_name="schools")
        op.drop_table("schools")
