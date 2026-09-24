import asyncio
from src.core.database import async_session_maker
from sqlalchemy import text
import json

async def main():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT dossier_data FROM triage_cases WHERE dni_reference = '90928086'"))
        row = res.fetchone()
        if row:
            # We don't want to print everything, just check if it's empty
            data = row[0]
            print("Beneficiario name:", data.get('beneficiary', {}).get('first_name'))

if __name__ == "__main__":
    asyncio.run(main())
