import asyncio
import sys
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import async_session_maker
from sqlalchemy import text

async def create_schools_table():
    """Crea la tabla schools que falta en las migraciones"""
    async with async_session_maker() as session:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS schools (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(200) UNIQUE NOT NULL,
                location VARCHAR(255),
                phone VARCHAR(50),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """))
        
        # Crear índice para is_active
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_schools_is_active ON schools (is_active)
        """))
        
        await session.commit()
        print("Tabla schools creada")

asyncio.run(create_schools_table())