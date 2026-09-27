# src/contexts/document_intake_ocr/domain/value_objects/raw_file.py
from dataclasses import dataclass
from typing import List, Optional

from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode
from src.contexts.document_intake_ocr.domain.value_objects.group_key import GroupKey


@dataclass(frozen=True)
class RawFile:
    file_name: str
    source_id: str

    @property
    def name_parts(self) -> List[str]:
        """Trozo del nombre sin extensión, partido por `_`.

        `"123456789_FINS_v2.pdf"` -> `["123456789", "FINS", "v2"]`. Es el
        parsing crudo que consumen `group_key` y `extracted_code`, y también
        el filtro, que necesita distinguir "no hay separador" de "el token no
        es numérico" para dar un mensaje accionable.
        """
        return self.file_name.rsplit('.', 1)[0].split('_')

    @property
    def group_key(self) -> Optional[GroupKey]:
        """Clave de agrupación del archivo: el token antes del primer `_`.

        Se devuelve tal cual venga, sin exigir que sea un DNI estándar: un
        token de 7 u 9 dígitos es casi siempre un error de tipeo del
        operador, no un documento ajeno, y descartarlo perdía el documento.
        Ver `GroupKey`.

        None solo si el nombre no sigue la convención `{DNI}_{CODIGO}.ext` o
        si el token no es numérico.
        """
        parts = self.name_parts
        if len(parts) < 2:
            return None
        token = parts[0].strip()
        if not token.isdigit():
            return None
        return GroupKey(token)

    @property
    def extracted_code(self) -> Optional[DocumentTypeCode]:
        """
        Extrae y valida el código del documento.
        Retorna el Value Object DocumentTypeCode si es válido, o None.
        """
        try:
            parts = self.name_parts
            if len(parts) >= 2:
                # Al instanciar DocumentTypeCode(), valida (ej. sin espacios, max caracteres)
                return DocumentTypeCode(parts[1])
            return None
        except ValueError:
            return None
        except Exception:
            return None
        
    @property
    def extension(self) -> str:
        """Extrae la extensión del archivo (ej. '.pdf', '.jpg')."""
        if '.' in self.file_name:
            return f".{self.file_name.rsplit('.', 1)[-1].lower()}"
        return ""
