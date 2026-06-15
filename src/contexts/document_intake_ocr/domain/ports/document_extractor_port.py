# src/contexts/document_intake_ocr/domain/ports/document_extractor_port.py
from typing import Protocol, Dict, Any
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import FileStream

class DocumentExtractorPort(Protocol):
    """
    Puerto de Salida (Outbound Port) para la extracción de datos.
    Abstrae cualquier motor de IA, OCR o parser que transforme 
    un flujo de bytes en un diccionario de datos estructurados.
    """
    def extract_data(self, document: FileStream, model_id: str) -> Dict[str, Any]:
        pass