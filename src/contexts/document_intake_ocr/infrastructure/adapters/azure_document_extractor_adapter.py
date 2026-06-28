# src/contexts/document_intake_ocr/infrastructure/adapters/azure_document_extractor.py

import logging
from typing import Dict, Any
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.core.exceptions import HttpResponseError

from src.contexts.document_intake_ocr.domain.ports.document_data_extractor import DocumentExtractor
from src.core.validators.exceptions import ExternalServiceException

logger = logging.getLogger(__name__)

class AzureDocumentExtractor(DocumentExtractor):
    """
    Adaptador de Infraestructura para Azure Document Intelligence.
    Implementa el puerto DocumentExtractor manejando I/O asíncrono.
    """
    def __init__(self, endpoint: str, key: str):
        self.endpoint = endpoint
        self.credential = AzureKeyCredential(key)
        # Cliente asíncrono para no bloquear el Event Loop de FastAPI
        self.client = DocumentAnalysisClient(
            endpoint=self.endpoint, 
            credential=self.credential
        )

    async def extract_data(self, file_bytes: bytes, model_id: str) -> Dict[str, Any]:
        logger.info(f"Iniciando extracción en Azure con el modelo: '{model_id}'")
        
        try:
            # 1. Enviar el documento a Azure (Operación Asíncrona Larga)
            poller = await self.client.begin_analyze_document(  
                model_id=model_id, 
                document=file_bytes
            )
            
            # 2. Esperar el resultado
            result = await poller.result()
            
            # 3. Parsear el resultado a nuestro formato de dominio
            extracted_fields = {}
            confidences = []

            # Azure puede devolver múltiples "documentos" lógicos en un solo archivo
            for analyzed_document in result.documents:
                for name, field in analyzed_document.fields.items():
                    # Extraemos el valor limpio (sea string, date, number, etc.)
                    extracted_fields[name] = field.value
                    
                    # Guardamos la confianza si existe
                    if field.confidence is not None:
                        confidences.append(field.confidence)

            # 4. Calcular el "Global Confidence Score" del documento
            # Promediamos la confianza de todos los campos extraídos
            global_confidence = 0.0
            if confidences:
                global_confidence = sum(confidences) / len(confidences)

            return {
                "fields": extracted_fields,
                "confidence": round(global_confidence, 4)
            }

        except HttpResponseError as e:
            # Capturamos errores específicos de Azure (ej. credenciales inválidas, modelo no existe)
            logger.error(f"Error de red/API con Azure: {e.message}")
            raise ExternalServiceException(f"Azure OCR Error: {e.message}")
            
        except Exception as e:
            # Fallos genéricos (ej. archivo corrupto)
            logger.error(f"Error procesando documento en Azure: {str(e)}")
            raise ExternalServiceException(f"Fallo inesperado de extracción: {str(e)}")
            
    async def close(self):
        """Buena práctica: cerrar la sesión HTTP asíncrona cuando se destruya el adaptador"""
        await self.client.close()