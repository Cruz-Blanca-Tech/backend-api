import asyncio
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT status FROM extraction_batches WHERE id = '8f773541-b142-430e-92ee-6270223039b2'"))
        row = res.fetchone()
        if row:
            print('Batch status:', row[0])

if __name__ == "__main__":
    asyncio.run(main())
