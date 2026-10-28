import asyncio
import json
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

def get_db_url() -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        try:
            from src.core.config import Settings
            db_url = Settings().ASYNC_DATABASE_URI
        except Exception:
            pass

    if not db_url:
        print("Error: DATABASE_URL environment variable must be set.", file=sys.stderr)
        sys.exit(1)

    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return db_url

async def check():
    db_url = get_db_url()
    dnis = sys.argv[1:]
    if not dnis:
        print("Uso: python inspect_dossier_data.py <dni_1> [<dni_2> ...]")
        return

    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        placeholders = ", ".join(f":dni_{i}" for i in range(len(dnis)))
        params = {f"dni_{i}": dni for i, dni in enumerate(dnis)}
        res = await conn.execute(
            text(f"SELECT dni_reference, dossier_data FROM triage_cases WHERE dni_reference IN ({placeholders})"),
            params
        )
        for r in res.fetchall():
            print("=== DNI:", r[0])
            print(json.dumps(r[1], indent=2, ensure_ascii=False)[:800])

if __name__ == "__main__":
    asyncio.run(check())
