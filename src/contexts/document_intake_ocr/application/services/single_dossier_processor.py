# src/contexts/document_intake_ocr/application/services/single_dossier_processor.py

import logging
from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
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

    async def execute(self, dossier: Dossier, target_folder_id: str, user_email: str) -> int:
        """
        Ejecuta el pipeline para todos los archivos del expediente.
        Retorna la cantidad de documentos procesados.
        """
        logger.info(f" -> Iniciando procesamiento de Expediente para DNI: {dossier.dni}")
        procesados = 0
        
        for doc in dossier.documents:
            if doc.status == DocumentStatus.FAILED:
                logger.debug(f"    Saltando documento {doc.file_name} (Fallo previo).")
                continue
            
            # Delegamos la I/O pesada al servicio que ya construimos
            await self.single_doc_processor.execute(doc, target_folder_id, user_email)
            procesados += 1
            
        # AQUÍ PODRÍAS AGREGAR LÓGICA DE DOSSIER:
        # Ej: dossier.evaluate_completion_status() si todos sus docs terminaron bien
            
        return procesados