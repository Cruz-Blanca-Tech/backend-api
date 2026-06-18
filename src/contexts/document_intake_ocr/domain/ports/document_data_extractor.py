# src/contexts/document_intake_ocr/domain/ports/document_extractor.py

from abc import ABC, abstractmethod
from typing import Dict, Any

class DocumentExtractor(ABC):
    """
    Puerto de dominio para la extracción de información estructurada mediante IA/OCR.
    Agnóstico al proveedor de tecnología (Azure, AWS, GCP, etc.).
    """
    
    @abstractmethod
    async def extract_data(self, file_bytes: bytes, model_id: str) -> Dict[str, Any]:
        """
        Analiza los bytes de un documento para recuperar sus datos estructurados.
        
        :param file_bytes: El contenido binario del documento a analizar.
        :param model_id: El identificador del modelo (ej. 'prebuilt-document', 'prebuilt-idDocument').
        :return: Un diccionario plano con los campos extraídos, listo para ser 
                 mapeado a las Entidades de Dominio.
        """
        pass