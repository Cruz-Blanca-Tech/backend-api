import asyncio
from sqlalchemy import text
from src.core.database import engine

async def check():
    async with engine.begin() as c:
        await c.execute(text("ALTER TABLE adults ADD COLUMN IF NOT EXISTS is_guardian BOOLEAN DEFAULT FALSE"))
        await c.execute(text("UPDATE adults SET is_guardian = TRUE FROM persons p WHERE p.id = adults.id AND p.dni = '76827414'"))

asyncio.run(check())
