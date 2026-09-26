import re

file_path = 'src/contexts/data_quality_triage/application/shared/handlers/triage_event_handler.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Buscamos la funcion handle_batch_ocr_completed y la deshabilitamos
target_code = "result = await use_case.execute(event.batch_id)"
replacement = """
        # DESACTIVADO: Evitar cierre automático del lote
        # result = await use_case.execute(event.batch_id)
        # logger.info(f"[Triage Event Handler] Resultado de la verificación automática: {result}")
        logger.info(f"[Triage Event Handler] Auto-cierre de lote desactivado para batch {event.batch_id}")
"""

if target_code in content:
    content = content.replace(target_code + "\n        logger.info(f\"[Triage Event Handler] Resultado de la verificacin automtica: {result}\")", replacement)
    # in case of strange encoding issues
    content = content.replace(target_code + "\n        logger.info(f\"[Triage Event Handler] Resultado de la verificaci\\ufffdn autom\\ufffdtica: {result}\")", replacement)
    
    # or just regex replace
    content = re.sub(r'result\s*=\s*await use_case.execute\(event.batch_id\).*?logger\.info\(f"\[Triage Event Handler\].*?"\)', replacement.strip(), content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Auto-cierre desactivado.")
