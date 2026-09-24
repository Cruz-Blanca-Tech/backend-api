import asyncio
import json
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT dossier_data FROM triage_cases WHERE dni_reference = '81184634' AND batch_id = '2fc57803-ff23-4258-868b-0b623573266b'"))
        row = res.fetchone()
        if row:
            d = row[0]
            print('--- EDUCATION ---')
            print(json.dumps(d.get('education', {}), indent=2))
            print('--- RELATED ADULTS ---')
            print(json.dumps(d.get('related_adults', {}), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
