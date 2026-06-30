"""create_operations_views

Revision ID: 69904a3010cd
Revises: 6cd0c83e8860
Create Date: 2026-06-30 01:33:25.242145

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69904a3010cd'
down_revision: Union[str, Sequence[str], None] = '6cd0c83e8860'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Success Rate View
    op.execute("""
        CREATE VIEW vw_ops_success_rate AS
        SELECT 
            status,
            COUNT(*) AS count
        FROM triage_cases
        GROUP BY status;
    """)

    # 2. Automation Level View
    op.execute("""
        CREATE VIEW vw_ops_automation_level AS
        SELECT 
            verdict,
            COUNT(*) AS count
        FROM triage_cases
        GROUP BY verdict;
    """)

    # 3. Daily Volume View
    op.execute("""
        CREATE VIEW vw_ops_daily_volume AS
        SELECT 
            to_char(created_at, 'YYYY-MM-DD') AS day,
            COUNT(*) AS total_cases
        FROM triage_cases
        GROUP BY to_char(created_at, 'YYYY-MM-DD');
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS vw_ops_daily_volume;")
    op.execute("DROP VIEW IF EXISTS vw_ops_automation_level;")
    op.execute("DROP VIEW IF EXISTS vw_ops_success_rate;")
