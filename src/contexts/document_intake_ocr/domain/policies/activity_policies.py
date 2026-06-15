# src/contexts/document_intake_ocr/domain/policies/activity_policy.py

from dataclasses import dataclass
from typing import Set, List
from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode
from src.contexts.document_intake_ocr.domain.entities.document_type import DocumentTypeConfig

@dataclass(frozen=True)
class ActivityPolicy:
    """
    Representa la 'Estrategia' de validación de una actividad.
    Es inmutable: se crea al cargar la actividad y vive solo lo que dure el proceso.
    """
    name: str
    required_documents: List[DocumentTypeConfig]

    @property
    def required_codes(self) -> Set[DocumentTypeCode]:
        """
        Retorna solo los códigos de documentos requeridos para la validación estructural.
        Es lo que tu SubBatch usa para el is_complete().
        """
        return {doc.code for doc in self.required_documents}

    def get_config_for_code(self, code: DocumentTypeCode) -> DocumentTypeConfig:
        """
        Consulta la configuración detallada (modelo IA, umbrales, etc.)
        para un código de documento específico.
        """
        for config in self.required_documents:
            if config.code == code:
                return config
        
        # Esto es vital para el motor de triaje o logs de errores
        raise ValueError(f"El documento {code} no está configurado para la actividad {self.name}")