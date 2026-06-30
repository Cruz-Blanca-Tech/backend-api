from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any

class SqlDemographicsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_population_pyramid(self) -> List[Dict[str, Any]]:
        query = text("SELECT * FROM vw_reporting_population_pyramid")
        result = await self.session.execute(query)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def get_registration_growth(self) -> List[Dict[str, Any]]:
        query = text("SELECT * FROM vw_reporting_registration_growth ORDER BY month ASC")
        result = await self.session.execute(query)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def get_document_coverage(self) -> List[Dict[str, Any]]:
        query = text("SELECT * FROM vw_reporting_document_coverage")
        result = await self.session.execute(query)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def get_raw_school_distribution(self) -> List[Dict[str, Any]]:
        query = text("SELECT * FROM vw_reporting_raw_schools")
        result = await self.session.execute(query)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def get_beneficiaries_master_export(self) -> List[Dict[str, Any]]:
        query = text("""
            SELECT 
                p.id,
                p.first_name || ' ' || p.last_name AS name,
                p.gender,
                EXTRACT(YEAR FROM age(current_date, p.birth_date)) AS age,
                e.school,
                CASE WHEN hd.id IS NOT NULL THEN 'SI' ELSE 'NO' END AS has_document
            FROM persons p
            LEFT JOIN education_records e ON p.id = e.beneficiary_id
            LEFT JOIN historical_documents hd ON hd.beneficiary_id = p.id
            WHERE p.type = 'beneficiary';
        """)
        result = await self.session.execute(query)
        rows = result.mappings().all()
        return [dict(r) for r in rows]
