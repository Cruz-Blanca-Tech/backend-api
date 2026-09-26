import asyncio
from sqlalchemy import text
from src.core.database import engine

async def check():
    async with engine.connect() as c:
        res = await c.execute(text("SELECT id, sync_error FROM triage_cases WHERE sync_status = 'FAILED'"))
        for row in res.fetchall():
            print(row)

asyncio.run(check())
