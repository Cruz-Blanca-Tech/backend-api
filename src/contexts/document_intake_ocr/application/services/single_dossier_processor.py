# src/contexts/document_intake_ocr/application/services/single_dossier_processor.py

import logging
from src.contexts.document_intake_ocr.domain.entities.activity import Activity
from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier, DossierStatus
from src.contexts.document_intake_ocr.domain.entities.document import DocumentStatus
from src.contexts.document_intake_ocr.application.services.single_document_processor import SingleDocumentProcessor

logger = logging.getLogger(__name__)

class SingleDossierProcessor:
    """
    Servicio de Aplicación: Orquesta el procesamiento de todos los documentos 
    pertenecientes a un único expediente (Dossier).
    """
    def __init__(self, single_doc_processor: SingleDocumentProcessor):
        # Inyectamos el procesador de documentos individuales
        self.single_doc_processor = single_doc_processor

    async def execute(self, dossier: Dossier, activity: Activity, target_folder_id: str, user_email: str) -> int:
        """
        Ejecuta el pipeline para todos los archivos del expediente.
        Retorna la cantidad de documentos procesados.
        """
        logger.info(f" -> Iniciando procesamiento de Expediente para clave de agrupación: {dossier.dni_reference}")
        procesados = 0

        # Un expediente incompleto NO entra al OCR. La UI ya impide subir un
        # lote con expedientes incompletos, así que llegar acá es la excepción
        # (un cliente que no pasa por la UI, un grupo mal tipeado). Gastar OCR
        # en los documentos que sí llegaron es tirar plata: cuando el operador
        # suba el que falta, `AppendDocumentsUseCase` reprocesa el expediente
        # entero. Los documentos quedan PENDING, que es justo el estado que ese
        # caso de uso busca para reprocesar, y el expediente se publica a
        # triaje con el ERROR "Falta el documento obligatorio: <doc>".
        if dossier.status == DossierStatus.INCOMPLETE:
            logger.warning(
                f"    Expediente {dossier.dni_reference} incompleto ({dossier.errors}). "
                "Se omite el OCR: se notificará en triaje para que se suba el documento faltante."
            )
            return 0

        for doc in dossier.documents:
            if doc.status == DocumentStatus.FAILED:
                logger.debug(f"    Saltando documento {doc.file_name} (Fallo previo).")
                continue
            
            try:
                model_id = activity.get_model_id_for_document(str(doc.document_code))
            except ValueError as e:
                doc.mark_as_failed(reason=str(e))
                continue
            
            # Delegamos la I/O pesada al servicio que ya construimos
            await self.single_doc_processor.execute(doc, model_id, target_folder_id, user_email)
            procesados += 1
            
        # Actualizamos el estado del expediente (COMPLETE o INCOMPLETE) en base a los requisitos
        dossier.update_status(activity.required_documents)
            
        return procesados