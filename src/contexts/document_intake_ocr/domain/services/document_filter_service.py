# src/contexts/document_intake_ocr/domain/services/document_filter_service.py
from dataclasses import dataclass
from typing import List, Tuple
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import RawFile

@dataclass(frozen=True)
class RejectedFile:
    file: RawFile
    reason: str

class DocumentFilterService:
    SUPPORTED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp'}

    @classmethod
    def filter_batch(cls, files: List[RawFile]) -> Tuple[List[RawFile], List[RejectedFile]]:
        valid_files = []
        rejected_files = []

        for f in files:
            # Validación jerárquica para dar el error más específico
            if f.extension not in cls.SUPPORTED_EXTENSIONS:
                rejected_files.append(RejectedFile(f, "Formato de archivo no soportado."))
            elif f.extracted_dni is None:
                rejected_files.append(RejectedFile(f, "DNI no encontrado o formato incorrecto en el nombre."))
            elif f.extracted_code is None:
                rejected_files.append(RejectedFile(f, "Código de documento no reconocido."))
            else:
                valid_files.append(f)

        return valid_files, rejected_files