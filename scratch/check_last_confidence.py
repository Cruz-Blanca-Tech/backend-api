import asyncio
from sqlalchemy import text
from src.core.database import async_session_maker

async def check_last_confidence():
    async with async_session_maker() as session:
        # Traer el ǧltimo expediente procesado de la tabla triage_cases
        query = text("""
            SELECT dni_reference, confidence_scores, created_at 
            FROM triage_cases 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        result = await session.execute(query)
        row = result.fetchone()
        
        if row:
            print("=========================================")
            print(f"DNI DEL EXPEDIENTE: {row.dni_reference}")
            print(f"FECHA DE PROCESO: {row.created_at}")
            print("=========================================")
            print("PUNTAJES DE CONFIANZA GLOBALES (POR CAMPO):")
            
            import json
            # El campo confidence_scores es un JSONB
            scores = row.confidence_scores if isinstance(row.confidence_scores, dict) else json.loads(row.confidence_scores)
            
            for field, score in scores.items():
                print(f" - {field}: {score * 100:.2f}%")
            print("=========================================")
        else:
            print("No hay expedientes en la base de datos.")

if __name__ == "__main__":
    asyncio.run(check_last_confidence())
