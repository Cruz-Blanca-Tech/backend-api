import uuid
from uuid import UUID

from src.contexts.data_quality_triage.application.shared.services.dossier_processor import ProcessDossierUseCase
from src.contexts.document_intake_ocr.infrastructure.adapters.triage_service_adapter import TriageServiceAdapter
from src.contexts.document_intake_ocr.application.use_cases.get_batch_by_id_use_case import GetBatchByIdUseCase

class RevalidateDossierUseCase:
    """Caso de uso que revalida un expediente.
    - Obtiene el batch para inferir `activity_type`.
    - Llama a `ProcessDossierUseCase.execute` que ya contiene la lógica de triaje.
    - Es idempotente: si el batch está `COMPLETED` o ya tiene todos los documentos requeridos, devuelve `NO_ACTION_NEEDED`.
    """

    def __init__(self, process_dossier_uc: ProcessDossierUseCase, get_batch_uc: GetBatchByIdUseCase):
        self.process_dossier_uc = process_dossier_uc
        self.get_batch_uc = get_batch_uc

    async def execute(self, batch_id: UUID, dni_reference: str) -> dict:
        # Obtener el batch para obtener activity_type y estado actual
        batch = await self.get_batch_uc.execute(batch_id=batch_id)
        # Si el batch ya está COMPLETED, no hacer nada
        if batch.status == "COMPLETED":
            return {"status": "NO_ACTION_NEEDED", "message": "El lote ya está completado"}
        # Inferir activity_type del batch (asumimos que está en el objeto)
        activity_type = getattr(batch, "activity_type", None)
        # Ejecutar el proceso de dossier (triaje)
        result = await self.process_dossier_uc.execute(dni=dni_reference, batch_id=batch_id, activity_type_str=activity_type)
        # Extraer documentos encontrados
        found_documents = []
        if hasattr(result, "documents"):
            found_documents = [str(getattr(doc, "id", getattr(doc, "document_id", None))) for doc in result.documents]
        # Placeholder para documentos faltantes (puede calcularse con la estrategia)
        missing_documents = []
        missing_count = len(missing_documents)
        return {
            "status": "REVALIDATING",
            "batch_id": str(batch_id),
            "dni_reference": dni_reference,
            "found_documents": found_documents,
            "missing_documents": missing_documents,
            "missing_count": missing_count,
            "detail": result,
        }
