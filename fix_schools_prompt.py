import re

with open('src/contexts/document_intake_ocr/infrastructure/adapters/llm_data_normalizer.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_rule = '''1. COLEGIOS (CLASIFICACION ESTRICTA):
         Existen unicamente 2 colegios validos: "SAN MARTIN" y "VILLAS".
         Debes mapear el colegio extraido a uno de estos dos valores si se parece semantica o foneticamente.
         Si el colegio escrito NO se parece a ninguno de estos dos (ej. es un colegio completamente distinto), DEBES poner el campo correspondiente a colegio como `null` y agregar un mensaje claro en el array de `warnings` indicando "Colegio no reconocido: [nombre extraido]". NO dejes el nombre original si no es SAN MARTIN o VILLAS.'''

content = re.sub(r'1\. COLEGIOS \(MDM\):.*?Si el colegio no se parece a ninguno, d.jalo tal cual\.', new_rule, content, flags=re.DOTALL)

with open('src/contexts/document_intake_ocr/infrastructure/adapters/llm_data_normalizer.py', 'w', encoding='utf-8') as f:
    f.write(content)
