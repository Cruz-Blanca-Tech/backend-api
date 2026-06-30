"""create_reporting_views

Revision ID: 6cd0c83e8860
Revises: b32dfcfecbca
Create Date: 2026-06-30 01:08:05.432053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6cd0c83e8860'
down_revision: Union[str, Sequence[str], None] = 'b32dfcfecbca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Population Pyramid View
    op.execute("""
        CREATE VIEW vw_reporting_population_pyramid AS
        WITH age_data AS (
            SELECT 
                gender,
                EXTRACT(YEAR FROM age(current_date, birth_date)) AS current_age
            FROM persons
            WHERE type = 'beneficiary' AND birth_date IS NOT NULL
        ),
        grouped_data AS (
            SELECT 
                gender,
                CASE 
                    WHEN current_age BETWEEN 0 AND 5 THEN '0-5 años'
                    WHEN current_age BETWEEN 6 AND 12 THEN '6-12 años'
                    WHEN current_age BETWEEN 13 AND 18 THEN '13-18 años'
                    ELSE '19+ años'
                END AS age_group
            FROM age_data
        )
        SELECT 
            age_group,
            SUM(CASE WHEN gender IN ('MALE', 'M') THEN 1 ELSE 0 END) AS male,
            SUM(CASE WHEN gender IN ('FEMALE', 'F') THEN 1 ELSE 0 END) AS female
        FROM grouped_data
        GROUP BY age_group;
    """)

    # 2. Registration Growth View
    op.execute("""
        CREATE VIEW vw_reporting_registration_growth AS
        SELECT 
            to_char(created_at, 'YYYY-MM') AS month,
            COUNT(*) AS new_beneficiaries
        FROM triage_cases
        WHERE status = 'APPROVED'
        GROUP BY to_char(created_at, 'YYYY-MM');
    """)

    # 3. Document Coverage View
    op.execute("""
        CREATE VIEW vw_reporting_document_coverage AS
        WITH stats AS (
            SELECT 
                p.id,
                CASE WHEN hd.id IS NOT NULL THEN 1 ELSE 0 END as has_doc
            FROM persons p
            LEFT JOIN historical_documents hd ON hd.beneficiary_id = p.id
            WHERE p.type = 'beneficiary'
        )
        SELECT 
            'Con Documento' as name, SUM(has_doc) as value
        FROM stats
        UNION ALL
        SELECT 
            'Sin Documento' as name, SUM(CASE WHEN has_doc = 0 THEN 1 ELSE 0 END) as value
        FROM stats;
    """)

    # 4. Raw Schools View (For dynamic aggregation in Python)
    op.execute("""
        CREATE VIEW vw_reporting_raw_schools AS
        SELECT 
            school,
            COUNT(*) AS total
        FROM education_records
        GROUP BY school;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS vw_reporting_raw_schools;")
    op.execute("DROP VIEW IF EXISTS vw_reporting_document_coverage;")
    op.execute("DROP VIEW IF EXISTS vw_reporting_registration_growth;")
    op.execute("DROP VIEW IF EXISTS vw_reporting_population_pyramid;")
