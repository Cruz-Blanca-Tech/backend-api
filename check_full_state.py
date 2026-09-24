import asyncio, json
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        # Check document_items extracted_data for the reprocessed batch
        res = await session.execute(text("""
            SELECT d.file_name, d.code, d.status, d.extracted_data, d.batch_id
            FROM document_items d 
            WHERE d.dni_reference = '90928086'
            ORDER BY d.processed_at DESC
        """))
        for r in res.fetchall():
            data = r[3] or {}
            has_data = len(data) > 0
            print(f'[{r[2]}] {r[0]} (code={r[1]}, batch={r[4]}) -> has_data={has_data}, keys={list(data.keys())[:5]}')
        
        # Check how many triage_cases exist for this DNI
        res2 = await session.execute(text("""
            SELECT id, batch_id, status, verdict, updated_at
            FROM triage_cases 
            WHERE dni_reference = '90928086'
        """))
        print('\n--- TRIAGE CASES ---')
        for r in res2.fetchall():
            print(f'ID={r[0]} batch={r[1]} status={r[2]} verdict={r[3]} updated={r[4]}')

asyncio.run(main())
