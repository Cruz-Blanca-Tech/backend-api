import asyncio
from sqlalchemy import update
from src.core.database import engine
from src.contexts.security_access.infrastructure.persistence.models.user_model import UserModel

async def make_admin():
    async with engine.begin() as conn:
        await conn.execute(update(UserModel).values(role='admin'))
        print("Updated all users to admin")

if __name__ == "__main__":
    asyncio.run(make_admin())
