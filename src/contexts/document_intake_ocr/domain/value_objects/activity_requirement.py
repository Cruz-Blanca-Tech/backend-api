# src/contexts/document_intake_ocr/domain/value_objects/activity_requirement.py
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.contexts.document_intake_ocr.domain.entities.document_type import DocumentTypeConfig


@dataclass(frozen=True)
class ActivityRequirement:
    """
    Value Object de Dominio: Representa la regla de negocio que el usuario 
    configuró para un documento dentro de una actividad específica.
    """
    document_config: DocumentTypeConfig              
    is_required: bool            
    confidence_threshold: float  
    
    @property
    def model_id(self) -> str:
        return self.document_config.model_id
    
    @property
    def config_id(self) -> UUID:
        """Expone el ID técnico encapsulando el acceso al config interno."""
        return self.document_config.id

    @property
    def code_str(self) -> str:
        """Expone el código de negocio en formato string de manera segura."""
        return str(self.document_config.code)

    def get_id_by_code(self, code_str: str) -> Optional[UUID]:
        """
        Retorna su config_id solo si el código solicitado coincide con 
        el código de su configuración interna.
        """
        if self.code_str == code_str:
            return self.config_id
        return None