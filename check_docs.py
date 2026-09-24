import asyncio
import json
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT id, code, file_name, status FROM document_items WHERE dni_reference = '81184634' AND batch_id = '2fc57803-ff23-4258-868b-0b623573266b'"))
        rows = res.fetchall()
        print("Documents for 81184634 in correct batch:")
        for row in rows:
            print(f"- {row[1]} ({row[2]}): {row[3]}")
        
        # Check discrepancies and document_ids
        res = await session.execute(text("SELECT document_ids, discrepancies FROM triage_cases WHERE dni_reference = '81184634' AND batch_id = '2fc57803-ff23-4258-868b-0b623573266b'"))
        row = res.fetchone()
        if row:
            print('Document IDs map in Triage Case:', json.dumps(row[0], indent=2))
            print('Discrepancies:', json.dumps(row[1], indent=2))

if __name__ == "__main__":
    asyncio.run(main())
