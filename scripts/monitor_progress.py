import asyncio
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
    batch_id = sys.argv[1] if len(sys.argv) > 1 else os.getenv("BATCH_ID")
    if not batch_id:
        print("Uso: python monitor_progress.py <batch_id> (o defina variable BATCH_ID)")
        return

    db_url = get_db_url()
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        res_batch = await conn.execute(
            text("SELECT id, status, description, created_by FROM extraction_batches WHERE id = :bid"),
            {"bid": batch_id}
        )
        batch = res_batch.fetchone()
        
        res_docs = await conn.execute(
            text("SELECT status, count(id) FROM document_items WHERE batch_id = :bid GROUP BY status"),
            {"bid": batch_id}
        )
        docs = res_docs.fetchall()
        
        res_cases = await conn.execute(
            text("SELECT count(id) FROM triage_cases WHERE batch_id = :bid"),
            {"bid": batch_id}
        )
        cases = res_cases.scalar()
        
        print(f"Batch Status: {batch[1] if batch else 'NOT FOUND'}")
        print(f"Document items: {dict(docs)}")
        print(f"Triage cases: {cases}")

if __name__ == "__main__":
    asyncio.run(check())
