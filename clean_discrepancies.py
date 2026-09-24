import asyncio
import json
import sys
sys.path.append(r"C:\Users\enzot\Documents\code\CruzBlanca\backend-api")

from src.core.database import engine
from sqlalchemy import text

GHOSTS = ["08TONA", "EVEN"]

async def clean_discrepancies():
    async with engine.begin() as conn:
        print("Buscando discrepancias con fantasmas OCR...")
        result = await conn.execute(text("SELECT id, discrepancies FROM triage_cases WHERE discrepancies IS NOT NULL"))
        cases = result.fetchall()
        
        updated = 0
        for case in cases:
            case_id = case.id
            disc = case.discrepancies
            if not disc:
                continue
            
            disc_str = json.dumps(disc) if not isinstance(disc, str) else disc
            if not any(g in disc_str.upper() for g in GHOSTS):
                continue
            
            disc_list = json.loads(disc_str) if isinstance(disc_str, str) else disc
            if not isinstance(disc_list, list):
                continue
            
            # Filtrar discrepancias que mencionan fantasmas
            cleaned = [d for d in disc_list if not any(g in json.dumps(d).upper() for g in GHOSTS)]
            
            print(f"  Limpiando discrepancias del caso {case_id}: {len(disc_list)} -> {len(cleaned)}")
            await conn.execute(
                text("UPDATE triage_cases SET discrepancies = :disc WHERE id = :id"),
                {"disc": json.dumps(cleaned), "id": case_id}
            )
            updated += 1
        
        print(f"Discrepancias limpiadas en {updated} casos.")

if __name__ == "__main__":
    asyncio.run(clean_discrepancies())
