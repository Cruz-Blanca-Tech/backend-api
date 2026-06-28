from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
from src.contexts.data_quality_triage.application.shared.services.normalize_registry import NormalizerRegistry
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.domain.shared.value_objects.enriched_field import EnrichedField

class BaseEnrichedMapper(ABC):
    def __init__(self, registry: NormalizerRegistry):
        self.registry = registry

    def build_field(self, raw_value: Any, friendly_name: str, data_type: DataType) -> EnrichedField:
        normalizer = self.registry.get(data_type)
        if normalizer:
            norm_val = normalizer.normalize(raw_value)
        else:
            norm_val = raw_value
            
        return EnrichedField(name=friendly_name, raw_value=raw_value, normalized_value=norm_val)

    @abstractmethod
    def map(self, raw_dto: Any) -> Any:
        pass
