import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import async_session_maker
from sqlalchemy import text

async def fix_activities_table():
    """Agrega columnas faltantes a la tabla activities"""
    async with async_session_maker() as session:
        # Verificar qué columnas existen
        result = await session.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'activities' AND table_schema = 'public'
        """))
        columns = [row[0] for row in result]
        print(f"Columnas actuales en activities: {columns}")
        
        if 'activity_type' not in columns:
            await session.execute(text("""
                ALTER TABLE activities 
                ADD COLUMN activity_type VARCHAR(50) DEFAULT 'UNKNOWN'
            """))
            print("Columna activity_type agregada")
        
        if 'start_date' not in columns:
            await session.execute(text("""
                ALTER TABLE activities 
                ADD COLUMN start_date DATE
            """))
            print("Columna start_date agregada")
            
        if 'end_date' not in columns:
            await session.execute(text("""
                ALTER TABLE activities 
                ADD COLUMN end_date DATE
            """))
            print("Columna end_date agregada")
        
        if 'is_active' not in columns:
            await session.execute(text("""
                ALTER TABLE activities 
                ADD COLUMN is_active BOOLEAN DEFAULT TRUE
            """))
            print("Columna is_active agregada")
        
        if 'program_id' not in columns:
            await session.execute(text("""
                ALTER TABLE activities 
                ADD COLUMN program_id UUID REFERENCES programs(id)
            """))
            print("Columna program_id agregada")
        
        if 'created_at' not in columns:
            await session.execute(text("""
                ALTER TABLE activities 
                ADD COLUMN created_at TIMESTAMPTZ DEFAULT now()
            """))
            print("Columna created_at agregada")
        
        await session.commit()
        print("Columnas faltantes agregadas a activities")

asyncio.run(fix_activities_table())