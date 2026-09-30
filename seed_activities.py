#!/usr/bin/env python3
"""
Script para crear/sembrar la actividad de inscripción EDUCA 2026 Semestre 2
Usa SQL directo para evitar problemas de relaciones ORM
"""

import asyncio
import sys
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import async_session_maker
from sqlalchemy import text

# ID del programa EDUCA existente
EDUCA_PROGRAM_ID = UUID("e561e788-f053-40cc-a4a3-5040627f27de")

# ID de la actividad existente (semestre 1) para actualizar su tipo
ACTIVIDAD_SEM1_ID = UUID("05194c0c-9ff7-4b4d-97f6-af51d62521c3")

async def seed_activities():
    async with async_session_maker() as session:
        # 1. Actualizar actividad semestre 1: corregir activity_type y fechas
        stmt1 = text("""
            UPDATE activities 
            SET activity_type = 'EDUCA_INSCRIPTION',
                start_date = :start_date,
                end_date = :end_date
            WHERE id = :id
        """)
        await session.execute(stmt1, {
            "id": str(ACTIVIDAD_SEM1_ID),
            "start_date": date(2026, 3, 15),
            "end_date": date(2026, 7, 15)
        })
        print(f"Actualizada actividad semestre 1 (ID: {ACTIVIDAD_SEM1_ID}) -> activity_type=EDUCA_INSCRIPTION, fechas 2026-03-15 a 2026-07-15")

        # 2. Verificar si ya existe actividad semestre 2
        check_sem2 = text("SELECT id FROM activities WHERE name = 'INSCRIPCIÓN A EDUCA 2026 - II'")
        result = await session.execute(check_sem2)
        existing = result.fetchone()

        if existing:
            # Actualizar existente
            stmt2 = text("""
                UPDATE activities 
                SET activity_type = 'EDUCA_INSCRIPTION',
                    start_date = :start_date,
                    end_date = :end_date,
                    is_active = true,
                    program_id = :program_id
                WHERE id = :id
            """)
            await session.execute(stmt2, {
                "id": str(existing[0]),
                "program_id": str(EDUCA_PROGRAM_ID),
                "start_date": date(2026, 7, 15),
                "end_date": date(2026, 11, 30)
            })
            print(f"Actualizada actividad semestre 2 (ID: {existing[0]}) -> activity_type=EDUCA_INSCRIPTION, fechas 2026-07-15 a 2026-11-30")
        else:
            # Crear nueva
            new_id = uuid4()
            stmt3 = text("""
                INSERT INTO activities (id, program_id, name, activity_type, start_date, end_date, is_active, created_at)
                VALUES (:id, :program_id, :name, :activity_type, :start_date, :end_date, :is_active, now())
            """)
            await session.execute(stmt3, {
                "id": str(uuid4()),
                "program_id": str(EDUCA_PROGRAM_ID),
                "name": "INSCRIPCIÓN A EDUCA 2026 - II",
                "activity_type": "EDUCA_INSCRIPTION",
                "start_date": date(2026, 7, 15),
                "end_date": date(2026, 11, 30),
                "is_active": True
            })
            print("Creada nueva actividad: INSCRIPCIÓN A EDUCA 2026 - II (semestre 2)")

        await session.commit()
        print("\n¡Actividades actualizadas/creadas correctamente!")

if __name__ == "__main__":
    asyncio.run(seed_activities())