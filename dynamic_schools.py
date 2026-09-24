import re

with open('src/contexts/document_intake_ocr/infrastructure/adapters/llm_data_normalizer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add necessary imports at the top
imports_to_add = '''
from sqlalchemy.future import select
from src.core.database import async_session_maker
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.school_model import SchoolModel
'''
if 'from src.core.database import async_session_maker' not in content:
    content = content.replace('import json', 'import json' + imports_to_add)

# 2. Modify the normalize function to fetch schools
fetch_schools_logic = '''
        valid_schools_str = ""
        try:
            async with async_session_maker() as session:
                res = await session.execute(select(SchoolModel.name).filter(SchoolModel.is_active == True))
                active_schools = [row[0] for row in res.all()]
                if active_schools:
                    valid_schools_str = ", ".join(f'"{s}"' for s in active_schools)
        except Exception as e:
            logger.warning(f"No se pudieron cargar los colegios del MDM: {e}")
            valid_schools_str = '"SAN MARTIN", "VILLAS"'
            
        system_prompt = f"""
'''

content = content.replace('system_prompt = f"""', fetch_schools_logic)

# 3. Modify the prompt to use {valid_schools_str} instead of hardcoding
new_prompt_rule = '''1. COLEGIOS (CLASIFICACION ESTRICTA):
         Existen unicamente los siguientes colegios validos (MDM): {valid_schools_str}.
         Debes mapear el colegio extraido a uno de estos valores si se parece semantica o foneticamente.
         Si el colegio escrito NO se parece a ninguno de la lista (ej. es un colegio completamente distinto), DEBES poner el campo correspondiente a colegio como `null` y agregar un mensaje claro en el array de `warnings` indicando "Colegio no reconocido: [nombre extraido]". NO dejes el nombre original si no pertenece a la lista de validos.'''

content = re.sub(r'1\. COLEGIOS \(CLASIFICACION ESTRICTA\):.*?NO dejes el nombre original si no es SAN MARTIN o VILLAS\.', new_prompt_rule, content, flags=re.DOTALL)

with open('src/contexts/document_intake_ocr/infrastructure/adapters/llm_data_normalizer.py', 'w', encoding='utf-8') as f:
    f.write(content)
