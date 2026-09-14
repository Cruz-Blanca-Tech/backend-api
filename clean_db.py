import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from src.core.config import settings

async def clear_db():
    print("Conectando a la base de datos para limpieza...")
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    try:
        async with engine.begin() as conn:
            print("Ejecutando TRUNCATE CASCADE...")
            await conn.execute(text("TRUNCATE TABLE extraction_batches, document_items, triage_cases CASCADE;"))
            print("¡Base de datos limpiada con éxito!")
    except Exception as e:
        print(f"Error limpiando BD: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(clear_db())
