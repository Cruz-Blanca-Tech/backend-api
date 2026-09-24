import asyncio
import json
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT dossier_data, discrepancies FROM triage_cases WHERE dni_reference = '81184634' AND batch_id = '2fc57803-ff23-4258-868b-0b623573266b'"))
        row = res.fetchone()
        if row:
            print('Dossier Data Adults:', json.dumps(row[0].get("related_adults"), indent=2))
            print('Discrepancies:', json.dumps(row[1], indent=2))
        else:
            print("Not found")

if __name__ == "__main__":
    asyncio.run(main())
