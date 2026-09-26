import asyncio
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT batch_id, status FROM triage_cases WHERE dni_reference = '81184634' ORDER BY updated_at DESC LIMIT 1"))
        row = res.fetchone()
        if row:
            print('Batch ID:', row[0])
            print('Status:', row[1])

if __name__ == "__main__":
    asyncio.run(main())
