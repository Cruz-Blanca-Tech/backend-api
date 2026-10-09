import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DB_URL = "postgresql+asyncpg://postgres.panujqoelvpjebiiohjf:NZqjyYr0yZ4oGQZS@aws-1-us-west-2.pooler.supabase.com:5432/postgres"
BATCH_ID = "720e3c54-0eb3-4e09-ba54-923dc7b40805"

async def check():
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:
        res_batch = await conn.execute(
            text("SELECT id, status, description, created_by FROM extraction_batches WHERE id = :bid"),
            {"bid": BATCH_ID}
        )
        batch = res_batch.fetchone()
        
        res_docs = await conn.execute(
            text("SELECT status, count(id) FROM document_items WHERE batch_id = :bid GROUP BY status"),
            {"bid": BATCH_ID}
        )
        docs = res_docs.fetchall()
        
        res_cases = await conn.execute(
            text("SELECT count(id) FROM triage_cases WHERE batch_id = :bid"),
            {"bid": BATCH_ID}
        )
        cases = res_cases.scalar()
        
        print(f"Batch Status: {batch[1] if batch else 'NOT FOUND'}")
        print(f"Document items: {dict(docs)}")
        print(f"Triage cases: {cases}")

if __name__ == "__main__":
    asyncio.run(check())
