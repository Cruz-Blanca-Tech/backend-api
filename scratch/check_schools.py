import asyncio
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        try:
            res = await session.execute(text("SELECT name, is_active FROM schools"))
            print(res.fetchall())
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
