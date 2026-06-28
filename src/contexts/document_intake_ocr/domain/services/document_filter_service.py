# src/contexts/document_intake_ocr/domain/services/document_filter_service.py
from dataclasses import dataclass
from typing import List, Tuple
from src.contexts.document_intake_ocr.domain.entities.activity import Activity
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import RawFile

@dataclass(frozen=True)
class RejectedFile:
    file: RawFile
    reason: str

class DocumentFilterService:
    SUPPORTED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp'}

    @classmethod
    def filter_batch(cls, files: List[RawFile], activity: Activity) -> Tuple[List[RawFile], List[RejectedFile]]:
        valid_files = []
        rejected_files = []

        for f in files:
            # Validación jerárquica para dar el error más específico
            if f.extension not in cls.SUPPORTED_EXTENSIONS:
                rejected_files.append(RejectedFile(f, "Formato de archivo no soportado."))
            elif f.extracted_dni is None:
                rejected_files.append(RejectedFile(f, "DNI no encontrado o formato incorrecto en el nombre."))
            elif f.extracted_code is None:
                rejected_files.append(RejectedFile(f, "Código de documento con formato inválido (mínimo 2 caracteres)."))
            elif activity.get_config_id_by_code(f.extracted_code.code) is None:
                # El código tiene formato válido pero no pertenece al catálogo de la actividad.
                rejected_files.append(RejectedFile(
                    f,
                    f"El código '{f.extracted_code.code}' no es un documento válido para esta actividad."
                ))
            else:
                valid_files.append(f)

        return valid_files, rejected_files