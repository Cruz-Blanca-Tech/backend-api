import asyncio
import sys
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import async_session_maker
from sqlalchemy import text

async def seed_programs():
    """Crea el programa EDUCA si no existe"""
    async with async_session_maker() as session:
        # Verificar si existe el programa EDUCA
        result = await session.execute(text("SELECT id FROM programs WHERE name = 'EDUCA'"))
        existing = result.fetchone()
        
        EDUCA_PROGRAM_ID = UUID("e561e788-f053-40cc-a4a3-5040627f27de")
        
        if existing:
            print(f"Programa EDUCA ya existe: {existing[0]}")
        else:
            await session.execute(text("""
                INSERT INTO programs (id, name, description, is_active, created_at)
                VALUES (:id, :name, :description, :is_active, now())
            """), {
                "id": str(EDUCA_PROGRAM_ID),
                "name": "EDUCA",
                "description": "Programa de Acompañamiento Educativo Integral",
                "is_active": True,
            })
            print("Programa EDUCA creado")
        
        await session.commit()
        print("Programa EDUCA listo")

asyncio.run(seed_programs())