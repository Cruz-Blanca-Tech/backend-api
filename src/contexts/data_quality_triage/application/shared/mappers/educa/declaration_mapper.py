from typing import Any, Dict
from src.contexts.data_quality_triage.application.shared.services.normalize_registry import NormalizerRegistry
from src.contexts.data_quality_triage.domain.educa.value_objects.declaration_data import DeclarationData
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType


class DeclarationMapper:
    def __init__(self, registry: NormalizerRegistry):
        self.dni_normalizer = registry.get(DataType.DNI)

    def map(self, dj_raw: Dict[str, Any]) -> DeclarationData:
        if not dj_raw:
            return DeclarationData()
            
        return DeclarationData(
            day=dj_raw.get("declaration_day"),
            month=dj_raw.get("declaration_month"),
            year=dj_raw.get("declaration_year"),
            child_dni=self.dni_normalizer.normalize(dj_raw.get("child_dni")),
            child_name=dj_raw.get("child_name"),
            father_dni=self.dni_normalizer.normalize(dj_raw.get("parents_father_dni")),
            mother_dni=self.dni_normalizer.normalize(dj_raw.get("parents_mother_dni")),
            father_name=dj_raw.get("parents_father_name"),
            mother_name=dj_raw.get("parents_mother_name")
        )
