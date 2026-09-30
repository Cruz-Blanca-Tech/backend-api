import asyncio
import sys
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import async_session_maker
from sqlalchemy import text

async def seed_activities():
    async with async_session_maker() as session:
        EDUCA_PROGRAM_ID = UUID("e561e788-f053-40cc-a4a3-5040627f27de")
        ACTIVIDAD_SEM1_ID = UUID("05194c0c-9ff7-4b4d-97f6-af51d62521c3")

        # Verificar si existe la actividad semestre 1
        result = await session.execute(text("SELECT id FROM activities WHERE id = :id"), {"id": str(ACTIVIDAD_SEM1_ID)})
        existing = result.fetchone()

        if existing:
            # Actualizar existente
            await session.execute(text("""
                UPDATE activities 
                SET activity_type = 'EDUCA_INSCRIPTION',
                    start_date = :start_date,
                    end_date = :end_date
                WHERE id = :id
            """), {
                "id": str(ACTIVIDAD_SEM1_ID),
                "start_date": date(2026, 3, 15),
                "end_date": date(2026, 7, 15)
            })
            print(f"Actualizada actividad semestre 1 (ID: {ACTIVIDAD_SEM1_ID})")
        else:
            # Crear nueva
            await session.execute(text("""
                INSERT INTO activities (id, program_id, name, activity_type, start_date, end_date, is_active, created_at)
                VALUES (:id, :program_id, :name, :activity_type, :start_date, :end_date, :is_active, now())
            """), {
                "id": str(ACTIVIDAD_SEM1_ID),
                "program_id": str(EDUCA_PROGRAM_ID),
                "name": "INSCRIPCIÓN A EDUCA 2026 - I",
                "activity_type": "EDUCA_INSCRIPTION",
                "start_date": date(2026, 3, 15),
                "end_date": date(2026, 7, 15),
                "is_active": True
            })
            print(f"Creada actividad semestre 1 (ID: {ACTIVIDAD_SEM1_ID})")

        # Verificar semestre 2
        result = await session.execute(text("SELECT id FROM activities WHERE name = 'INSCRIPCIÓN A EDUCA 2026 - II'"))
        existing2 = result.fetchone()

        if not existing2:
            new_id = uuid4()
            await session.execute(text("""
                INSERT INTO activities (id, program_id, name, activity_type, start_date, end_date, is_active, created_at)
                VALUES (:id, :program_id, :name, :activity_type, :start_date, :end_date, :is_active, now())
            """), {
                "id": str(new_id),
                "program_id": str(EDUCA_PROGRAM_ID),
                "name": "INSCRIPCIÓN A EDUCA 2026 - II",
                "activity_type": "EDUCA_INSCRIPTION",
                "start_date": date(2026, 7, 15),
                "end_date": date(2026, 11, 30),
                "is_active": True
            })
            print("Creada actividad semestre 2")

        await session.commit()
        print("\n¡Actividades listas!")

asyncio.run(seed_activities())