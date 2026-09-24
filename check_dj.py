import asyncio
import json
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT file_name, extracted_data FROM document_items WHERE dni_reference = '90928086' AND code = 'DJ'"))
        row = res.fetchone()
        if row:
            print('Archivo:', row[0])
            print('Extraccion:', json.dumps(row[1], indent=2))

if __name__ == '__main__':
    asyncio.run(main())
