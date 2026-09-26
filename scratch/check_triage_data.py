import asyncio, json
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT dossier_data, updated_at FROM triage_cases WHERE dni_reference = '90928086'"))
        for r in res.fetchall():
            data = r[0]
            updated = r[1]
            print(f'Updated at: {updated}')
            ben = data.get('beneficiary', {})
            print(f'  Beneficiary DNI: {ben.get("dni")}')
            print(f'  Beneficiary First Name: {ben.get("first_name")}')
            print(f'  Beneficiary Last Name: {ben.get("last_name")}')
            edu = data.get('education', {})
            print(f'  Education Grade: {edu.get("grade")}')
            print(f'  Education School: {edu.get("school")}')
            adults = data.get('related_adults', {})
            print(f'  Guardian DNI: {adults.get("guardian_dni")}')
            print(f'  Adults count: {len(adults.get("adults", []))}')

asyncio.run(main())
