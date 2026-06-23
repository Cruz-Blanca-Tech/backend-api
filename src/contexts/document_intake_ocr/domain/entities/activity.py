# src/contexts/document_intake_ocr/domain/entities/activity.py
from dataclasses import dataclass, field
from uuid import UUID
from typing import List, Dict, Optional

from src.contexts.document_intake_ocr.domain.policies.activity_policies import ActivityPolicy
from src.contexts.document_intake_ocr.domain.value_objects.activity_requirement import ActivityRequirement

@dataclass
class Activity:
    """
    Agregado Raíz que representa una instancia operativa real en la Asociación Cruz Blanca.
    Protege sus invariantes asegurando que no existan requisitos documentales duplicados
    y provee resolución O(1) para la hidratación de documentos.
    """
    id: UUID
    program_id: UUID
    name: str  # Ej: "Inscripción 2026-I"
    required_documents: List[ActivityRequirement]
    is_active: bool
    
    # Mapa en memoria privado. No se expone en el constructor (init=False)
    _config_map: Dict[str, UUID] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """
        Se ejecuta automáticamente al instanciar.
        Construye el estado interno y valida las reglas de negocio críticas.
        """
        seen_ids = set()
        self._config_map = {}

        for req in self.required_documents:
            # Consumo limpio delegando en las propiedades del Value Object
            config_id = req.config_id
            code_value = req.code_str

            # Validación de Invariantes (Fail-Fast)
            if config_id in seen_ids:
                raise ValueError(
                    f"Invariante roto: La configuración '{config_id}' "
                    f"está duplicada en la actividad '{self.name}'."
                )
            if code_value in self._config_map:
                raise ValueError(
                    f"Invariante roto: El código '{code_value}' "
                    f"está duplicado en la actividad '{self.name}'."
                )

            seen_ids.add(config_id)
            # Construcción del índice O(1)
            self._config_map[code_value] = config_id

    def get_config_id_by_code(self, code_str: str) -> Optional[UUID]:
        """
        Delega la responsabilidad de búsqueda al experto en información.
        Permite al Caso de Uso y a la Fábrica encontrar el ID técnico sin esfuerzo.
        """
        return self._config_map.get(code_str)
    
    def get_model_id_for_document(self, code_str: str) -> str:
        """
        Busca en los requerimientos de la actividad el modelo de IA 
        que corresponde a un código de documento específico.
        """
        for req in self.required_documents:
            if req.code_str == code_str:
                return req.document_config.model_id  # Usa la propiedad que creamos antes
        raise ValueError(f"El código {code_str} no es un requerimiento válido para esta actividad.")
                
    def get_policy(self) -> ActivityPolicy:
        """
        La Entidad genera su propia Estrategia de validación (Policy)
        para ser consumida por el motor de evaluación de expedientes.
        """
        return ActivityPolicy(
            name=self.name,
            required_configs=self.required_documents
        )