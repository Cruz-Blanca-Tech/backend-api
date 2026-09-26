import asyncio
from src.core.database import engine
from sqlalchemy import text

async def recreate_views():
    async with engine.begin() as conn:
        print("Recreando vistas de operaciones...")
        # Operations
        await conn.execute(text("DROP VIEW IF EXISTS vw_ops_success_rate CASCADE;"))
        await conn.execute(text("""
            CREATE VIEW vw_ops_success_rate AS
            SELECT 
                status,
                COUNT(*) AS count
            FROM triage_cases
            GROUP BY status;
        """))
        
        await conn.execute(text("DROP VIEW IF EXISTS vw_ops_automation_level CASCADE;"))
        await conn.execute(text("""
            CREATE VIEW vw_ops_automation_level AS
            SELECT 
                verdict,
                COUNT(*) AS count
            FROM triage_cases
            GROUP BY verdict;
        """))
        
        await conn.execute(text("DROP VIEW IF EXISTS vw_ops_daily_volume CASCADE;"))
        await conn.execute(text("""
            CREATE VIEW vw_ops_daily_volume AS
            SELECT 
                to_char(created_at, 'YYYY-MM-DD') AS day,
                COUNT(*) AS total_cases
            FROM triage_cases
            GROUP BY to_char(created_at, 'YYYY-MM-DD');
        """))

        print("Recreando vistas de reportes...")
        # Reporting
        await conn.execute(text("DROP VIEW IF EXISTS vw_reporting_population_pyramid CASCADE;"))
        await conn.execute(text("""
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
        """))

        await conn.execute(text("DROP VIEW IF EXISTS vw_reporting_registration_growth CASCADE;"))
        await conn.execute(text("""
            CREATE VIEW vw_reporting_registration_growth AS
            SELECT 
                to_char(created_at, 'YYYY-MM') AS month,
                COUNT(*) AS new_beneficiaries
            FROM triage_cases
            WHERE status = 'APPROVED'
            GROUP BY to_char(created_at, 'YYYY-MM');
        """))

        await conn.execute(text("DROP VIEW IF EXISTS vw_reporting_document_coverage CASCADE;"))
        await conn.execute(text("""
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
        """))

        await conn.execute(text("DROP VIEW IF EXISTS vw_reporting_raw_schools CASCADE;"))
        await conn.execute(text("""
            CREATE VIEW vw_reporting_raw_schools AS
            SELECT 
                school,
                COUNT(*) AS total
            FROM education_records
            GROUP BY school;
        """))

    print("¡Vistas recreadas con éxito!")

if __name__ == "__main__":
    asyncio.run(recreate_views())
