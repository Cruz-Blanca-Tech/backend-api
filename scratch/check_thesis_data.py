import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from src.core.config import settings
import json

async def check_last_document():
    print("Conectando a la base de datos con SQL puro...")
    # Crear motor conectado directo a la BD sin ORM
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    
    try:
        async with engine.begin() as conn:
            # Seleccionar el último documento que tenga datos reales extraídos
            query = text('''
                SELECT file_name, confidence_score, extracted_data
                FROM document_items
                WHERE extracted_data IS NOT NULL 
                  AND extracted_data::text != '{}'
                ORDER BY processed_at DESC NULLS LAST
                LIMIT 1
            ''')
            result = await conn.execute(query)
            row = result.fetchone()

            if not row:
                print("No se encontro ningun documento procesado aun. Sube uno desde el Frontend!")
                return

            file_name, confidence_score, extracted_data = row
            
            print(f"\nUltimo Documento Encontrado: {file_name}")
            print(f"Promedio de Confianza Global: {confidence_score}")
            print("\nDatos Extraidos en PostgreSQL (JSONB):")
            print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
            
            # Verificación
            sample_key = next(iter(extracted_data)) if extracted_data else None
            if sample_key and isinstance(extracted_data[sample_key], dict) and "confidence" in extracted_data[sample_key]:
                print("\nEXITO: El backend esta guardando el % de IA por campo correctamente para tu tesis.")
            else:
                print("\nAVISO: El documento tiene la estructura antigua. Sube uno nuevo para ver el cambio.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_last_document())
