from abc import ABC, abstractmethod
from typing import List, Any
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy

class DocumentRule(ABC):
    """
    Interface para reglas de validación de Etapa 1 (Document-Level).
    Se ejecutan sobre los diccionarios o modelos enriquecidos de documentos.
    """
    @abstractmethod
    def evaluate(self, enriched_fins: Any = None, enriched_dj: Any = None, **kwargs) -> List[FieldDiscrepancy]:
        pass

class DomainRule(ABC):
    """
    Interface para reglas de validación de Etapa 2 (Domain-Level).
    Se ejecutan sobre la entidad consolidada de dominio final.
    """
    @abstractmethod
    def evaluate(self, domain_entity: Any) -> List[FieldDiscrepancy]:
        pass
