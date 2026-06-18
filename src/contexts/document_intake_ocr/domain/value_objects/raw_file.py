# src/contexts/document_intake_ocr/domain/value_objects/raw_file.py
from dataclasses import dataclass
from typing import Optional

from src.contexts.document_intake_ocr.domain.value_objects.dni import DNI
from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode

@dataclass(frozen=True)
class RawFile:
    file_name: str
    source_id: str

    @property
    def extracted_dni(self) -> Optional[DNI]:
        """
        Extrae y valida el DNI del nombre del archivo.
        Retorna el Value Object DNI si es válido, o None si el formato falla.
        """
        try:
            parts = self.file_name.rsplit('.', 1)[0].split('_')
            if len(parts) >= 2:
                # Al instanciar DNI(), se ejecutan las reglas de validación (ej: 8 dígitos)
                return DNI(parts[0]) 
            return None
        except ValueError:
            # Si el DNI(parts[0]) lanza error por ser inválido, retornamos None
            return None
        except Exception:
            return None

    @property
    def extracted_code(self) -> Optional[DocumentTypeCode]:
        """
        Extrae y valida el código del documento.
        Retorna el Value Object DocumentTypeCode si es válido, o None.
        """
        try:
            parts = self.file_name.rsplit('.', 1)[0].split('_')
            if len(parts) >= 2:
                # Al instanciar DocumentTypeCode(), valida (ej: sin espacios, max caracteres)
                return DocumentTypeCode(parts[1])
            return None
        except ValueError:
            return None
        except Exception:
            return None
        
    @property
    def extension(self) -> str:
        """Extrae la extensión del archivo (ej: '.pdf', '.jpg')."""
        if '.' in self.file_name:
            return f".{self.file_name.rsplit('.', 1)[-1].lower()}"
        return ""