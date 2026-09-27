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
        """Separa los archivos agrupables de los que no se pueden archivar.

        **La longitud del token de DNI no es motivo de rechazo.** Si lo fuera,
        un `123456789_FINS.pdf` (un dígito de más al tipear el nombre) se
        perdía entero, sin expediente y sin forma de recuperarlo. El token
        numérico de cualquier largo se acepta y se agrupa tal cual; que sea
        o no un DNI estándar lo decide el consumidor de `GroupKey`, y el DNI
        real del beneficiario lo aporta el OCR del documento.

        Lo que sí se rechaza es lo que no tiene arreglo por grouping: no se
        puede saber a qué expediente pertenece el archivo, o el tipo de
        documento no pertenece a esta actividad.
        """
        valid_files = []
        rejected_files = []

        for f in files:
            # Validación jerárquica para dar el error más específico
            if f.extension not in cls.SUPPORTED_EXTENSIONS:
                rejected_files.append(RejectedFile(f, "Formato de archivo no soportado."))
            elif f.group_key is None:
                # Sin clave de agrupación no hay expediente al que colgarlo.
                # Distinguimos los dos casos porque la solución es distinta:
                # renombrar el archivo (arreglo de 5 segundos) o descartar.
                if len(f.name_parts) < 2:
                    rejected_files.append(RejectedFile(
                        f,
                        "El nombre del archivo no sigue la convención "
                        "{DNI}_{CODIGO}.ext: no se encontró el separador '_'."
                    ))
                else:
                    rejected_files.append(RejectedFile(
                        f,
                        f"El identificador '{f.name_parts[0].strip()}' no es numérico, "
                        "así que no se puede agrupar el archivo en un expediente."
                    ))
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
