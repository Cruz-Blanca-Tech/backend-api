import re

with open('src/contexts/document_intake_ocr/infrastructure/adapters/llm_data_normalizer.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_rule = '''9. CRUCE Y CONSOLIDACI"N DE PADRES/APODERADOS (DETECCI"N DE G"NERO OBLIGATORIA):
         - INFERENCIA DE G"NERO: Debes analizar semánticamente el nombre extraído. Si el nombre en `parents_father_full_name` es evidentemente de mujer (ej. "Laura", "María", "Carmen"), ES UN ERROR DEL OCR O DEL LLM ANTERIOR. DEBES mover ese valor inmediatamente a `parents_mother_full_name` o `parents_guardian_full_name` y dejar el padre como `null`. NUNCA asignes a una mujer al rol de Padre.
         - De igual forma, si en `parents_mother_full_name` hay un nombre de hombre (ej. "Mario", "Juan", "Pedro"), muévelo a `parents_father_full_name`.
         - Si una misma persona fue extraída fragmentada en dos campos (ej. "Laura Sondoval Urguia" en el campo Padre y "Sondoval" en el campo Apoderado), asume que es la misma persona. Consolida su nombre completo en el rol correcto (Madre o Apoderado según su género) y deja el campo incorrecto en `null` o vacío. No dejes personas duplicadas o fragmentadas.

      Devuelve'''

content = re.sub(r'9\. CRUCE Y CONSOLIDACI.*?Devuelve', new_rule, content, flags=re.DOTALL)

with open('src/contexts/document_intake_ocr/infrastructure/adapters/llm_data_normalizer.py', 'w', encoding='utf-8') as f:
    f.write(content)
