import asyncio
import json
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT status, verdict, discrepancies, document_ids FROM triage_cases WHERE dni_reference = '81184634'"))
        row = res.fetchone()
        if row:
            print('Status:', row[0])
            print('Verdict:', row[1])
            print('Document IDs:', json.dumps(row[3], indent=2))
            print('Discrepancies:', json.dumps(row[2], indent=2))
        else:
            print("No case found for 81184634")

if __name__ == "__main__":
    asyncio.run(main())
