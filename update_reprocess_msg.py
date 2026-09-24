import re

file_path = 'src/contexts/document_intake_ocr/application/use_cases/reprocess_dossier_use_case.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''
        # Process synchronously! This keeps the HTTP request alive and the UI in "loading" state.
        await self._process_synchronously(batch, activity, target_dossier, user_email)

        # Check if they failed
        failed_count = sum(1 for d in target_dossier.documents if d.status.value == "FAILED")
        total_count = len(target_dossier.documents)
        
        if failed_count == total_count and total_count > 0:
            return {"message": "El reprocesamiento finalizó, pero todos los documentos fallaron en el OCR."}
        elif failed_count > 0:
            return {"message": f"Reprocesamiento completado. {failed_count} documentos fallaron."}

        return {"message": f"Expediente {dni_reference} reprocesado con éxito ({total_count} docs)."}
'''

content = re.sub(
    r'# Process synchronously! This keeps the HTTP request alive and the UI in "loading" state\.\s*await self\._process_synchronously\(batch, activity, target_dossier, user_email\)\s*return \{"message": f"Expediente \{dni_reference\} reprocesado con éxito\."\}',
    replacement.strip(),
    content
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
