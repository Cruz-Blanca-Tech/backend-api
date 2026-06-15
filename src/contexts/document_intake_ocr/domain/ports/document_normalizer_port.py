# src/contexts/document_intake_ocr/domain/ports/document_normalizer_port.py
from typing import Protocol
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import FileStream

class DocumentNormalizerPort(Protocol):
    """
    Puerto de Salida (Outbound Port) para la estandarización de archivos.
    Garantiza que cualquier archivo gráfico ingresado sea transformado 
    al formato estándar requerido por el Motor de Extracción y Custodia.
    """
    def normalize(self, raw_stream: FileStream) -> FileStream:
        """
        Recibe un FileStream en formato no estándar (ej. JPG/PNG) 
        y retorna un nuevo FileStream normalizado (ej. PDF).
        """
        pass