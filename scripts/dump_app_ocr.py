import asyncio
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DB_URL = "postgresql+asyncpg://postgres.panujqoelvpjebiiohjf:NZqjyYr0yZ4oGQZS@aws-1-us-west-2.pooler.supabase.com:5432/postgres"

async def check():
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT dni_reference, dossier_data FROM triage_cases WHERE dni_reference IN ('90928086', '90368548', '78996539') ORDER BY dni_reference")
        )
        for dni, data in res.fetchall():
            print(f"\n==================== DNI {dni} ====================")
            print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(check())
