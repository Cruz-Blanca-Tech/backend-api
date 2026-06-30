from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any

class SqlOperationsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_success_rate(self) -> List[Dict[str, Any]]:
        query = text("SELECT * FROM vw_ops_success_rate")
        result = await self.session.execute(query)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def get_automation_level(self) -> List[Dict[str, Any]]:
        query = text("SELECT * FROM vw_ops_automation_level")
        result = await self.session.execute(query)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def get_daily_volume(self) -> List[Dict[str, Any]]:
        query = text("SELECT * FROM vw_ops_daily_volume ORDER BY day ASC")
        result = await self.session.execute(query)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def get_rejected_cases_export(self) -> List[Dict[str, Any]]:
        query = text("""
            SELECT 
                id,
                dni_reference,
                to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at,
                rejection_reason
            FROM triage_cases
            WHERE status = 'REJECTED'
            ORDER BY created_at DESC;
        """)
        result = await self.session.execute(query)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def get_ocr_audit_export(self) -> List[Dict[str, Any]]:
        query = text("""
            SELECT 
                id,
                batch_id,
                dni_reference,
                status,
                verdict,
                confidence_scores,
                resolved_by,
                to_char(resolved_at, 'YYYY-MM-DD HH24:MI:SS') AS resolved_at,
                to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at
            FROM triage_cases
            ORDER BY created_at DESC;
        """)
        result = await self.session.execute(query)
        rows = result.mappings().all()
        return [dict(r) for r in rows]
