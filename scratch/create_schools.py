import asyncio
import uuid
from src.core.database import async_session_maker
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.school_model import SchoolModel
from sqlalchemy.future import select

async def main():
    async with async_session_maker() as session:
        # Check if exists
        res1 = await session.execute(select(SchoolModel).filter_by(name="SAN MARTIN"))
        s1 = res1.scalar_one_or_none()
        if not s1:
            s1 = SchoolModel(id=uuid.uuid4(), name="SAN MARTIN", location="Inventado 1", phone="12345678", is_active=True)
            session.add(s1)

        res2 = await session.execute(select(SchoolModel).filter_by(name="VILLAS"))
        s2 = res2.scalar_one_or_none()
        if not s2:
            s2 = SchoolModel(id=uuid.uuid4(), name="VILLAS", location="Inventado 2", phone="87654321", is_active=True)
            session.add(s2)

        await session.commit()
        print("Escuelas insertadas exitosamente.")

if __name__ == "__main__":
    asyncio.run(main())
