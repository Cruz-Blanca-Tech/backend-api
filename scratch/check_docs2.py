import asyncio
import json
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT id, code, file_name, extracted_data FROM document_items WHERE dni_reference = '81184634' AND batch_id = '2fc57803-ff23-4258-868b-0b623573266b'"))
        rows = res.fetchall()
        print("Documents for 81184634 in correct batch:")
        for row in rows:
            print(f"- ID: {row[0]}, Code: {row[1]}, Extracted keys: {list(row[3].keys()) if row[3] else None}")

if __name__ == "__main__":
    asyncio.run(main())
