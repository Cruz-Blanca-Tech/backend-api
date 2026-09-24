import asyncio
import json
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT dossier_data FROM triage_cases WHERE dni_reference = '81184634'"))
        row = res.fetchone()
        if row:
            print('Dossier Data:', json.dumps(row[0], indent=2))
        else:
            print("No case found for 81184634")

if __name__ == "__main__":
    asyncio.run(main())
