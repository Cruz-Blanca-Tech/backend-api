# src/contexts/document_intake_ocr/application/services/single_document_processor.py

import logging
from typing import Optional, Dict, Any
from src.contexts.document_intake_ocr.domain.entities.document import DocumentItem
from src.contexts.document_intake_ocr.domain.ports.document_data_extractor import DocumentExtractor
from src.contexts.document_intake_ocr.domain.ports.document_storage import DocumentStorage
from src.contexts.document_intake_ocr.domain.ports.data_normalizer import DataNormalizer
from src.contexts.document_intake_ocr.domain.value_objects.file_item import FileItem
from src.core.validators.exceptions import ExternalServiceException

logger = logging.getLogger(__name__)

class SingleDocumentProcessor:
    """
    Servicio de Aplicación Interno: Centraliza el flujo de I/O de un único 
    documento físico (Custodia en Bóveda -> Descarga a RAM -> Extracción OCR -> Normalización LLM).
    """
    def __init__(
        self, 
        storage_adapter: DocumentStorage, 
        extractor_adapter: DocumentExtractor,
        normalizer_adapter: Optional[DataNormalizer] = None
    ):
        self.storage = storage_adapter
        self.extractor = extractor_adapter
        self.normalizer = normalizer_adapter

    async def execute(
        self, 
        doc: DocumentItem, 
        model_id: str, 
        target_folder_id: str, 
        user_email: str,
        normalization_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Ejecuta el pipeline completo mutando el estado de la entidad DocumentItem.
        """
        logger.info(f"  -> Procesando documento: {doc.file_name} (DNI Ref: {doc.dni_reference})")
        
        try:
            file_item = FileItem(file_id=doc.source_id, file_name=doc.file_name)
            
            # --- FASE 1: CUSTODIA FÍSICA ---
            logger.debug(f"     [1/4] Copiando a bóveda de seguridad...")
            vault_uri = await self.storage.copy_to_custody(file_item, target_folder_id, user_email)
            doc.secure_in_custody(vault_uri)
            
            # --- FASE 2: DESCARGA A MEMORIA ---
            logger.debug(f"     [2/4] Descargando bytes a memoria RAM...")
            doc.mark_as_processing()
            file_bytes = await self.storage.download_file(file_item, user_email)

            ## --- FASE 3: EXTRACCIÓN OCR ---
            logger.debug(f"     [3/4] Enviando a motor OCR de Azure...")
            ocr_result = await self.extractor.extract_data(file_bytes, model_id)
            
            final_data = ocr_result.get("fields", {})
            
            ## --- FASE 4: NORMALIZACIÓN LLM (Opcional) ---
            if self.normalizer and final_data:
                logger.debug(f"     [4/4] Normalizando datos extraídos vía LLM...")
                final_data = await self.normalizer.normalize(final_data, normalization_context)
            else:
                logger.debug(f"     [4/4] Normalización LLM saltada (no configurada).")

            ## Registrar éxito
            doc.mark_as_processed_successfully(
                data=final_data, 
                confidence=ocr_result.get("confidence", 0.0)
            )
            logger.info(f"  -> [OK] Documento {doc.file_name} extraído y normalizado correctamente.")
            
        except ExternalServiceException as ext_error:
            logger.warning(f"  -> [FALLO EXTERNO] {doc.file_name}: {ext_error.message}")
            doc.mark_as_failed(reason=f"Servicio no disponible: {ext_error.message}")
            
        except Exception as e:
            logger.error(f"  -> [ERROR INTERNO] {doc.file_name}: {str(e)}")
            doc.mark_as_failed(reason=f"Error inesperado procesando archivo: {str(e)}")