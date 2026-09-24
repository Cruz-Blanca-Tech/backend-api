import asyncio
import json
import sys

# Set up path so src imports work
sys.path.append(r"C:\Users\enzot\Documents\code\CruzBlanca\backend-api")

from src.core.database import engine
from sqlalchemy import text

GHOSTS = ["08TONA", "EVEN"]

def clean_dict(data):
    if isinstance(data, dict):
        for k, v in list(data.items()):
            if isinstance(v, str) and any(g in v.upper() for g in GHOSTS):
                data[k] = None
            else:
                data[k] = clean_dict(v)
    elif isinstance(data, list):
        new_list = []
        for item in data:
            if isinstance(item, str) and any(g in item.upper() for g in GHOSTS):
                continue
            cleaned = clean_dict(item)
            if isinstance(cleaned, dict) and "name" in cleaned and cleaned.get("name") is None:
                continue
            new_list.append(cleaned)
        return new_list
    elif isinstance(data, str):
        if any(g in data.upper() for g in GHOSTS):
            return None
    return data

async def run_cleanup():
    async with engine.begin() as conn:
        print("Buscando casos en la bandeja (triage_cases)...")
        result = await conn.execute(text("SELECT id, dossier_data FROM triage_cases"))
        cases = result.fetchall()
        
        updated_count = 0
        for case in cases:
            case_id = case.id
            dossier_data = case.dossier_data
            
            if not dossier_data:
                continue
                
            data_dict = dossier_data if isinstance(dossier_data, dict) else json.loads(dossier_data)
            
            data_str = json.dumps(data_dict).upper()
            if not any(g in data_str for g in GHOSTS):
                continue
                
            print(f"Limpiando caso ID: {case_id}")
            cleaned_data = clean_dict(data_dict)
            
            # Update specific case
            await conn.execute(
                text("UPDATE triage_cases SET dossier_data = :data WHERE id = :id"),
                {"data": json.dumps(cleaned_data), "id": case_id}
            )
            updated_count += 1
            
        print(f"Limpieza completada. {updated_count} casos actualizados en la base de datos.")

if __name__ == "__main__":
    asyncio.run(run_cleanup())
