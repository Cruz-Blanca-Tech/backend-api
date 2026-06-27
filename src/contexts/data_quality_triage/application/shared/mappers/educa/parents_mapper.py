from typing import Any, Dict
from src.contexts.data_quality_triage.application.shared.normalizers.base import FieldNormalizer
from src.contexts.data_quality_triage.application.shared.services.normalize_registry import NormalizerRegistry
from src.contexts.data_quality_triage.domain.educa.value_objects.parent_detail import ParentDetail
from src.contexts.data_quality_triage.domain.educa.value_objects.parents_data import ParentsData
from src.contexts.data_quality_triage.domain.educa.value_objects.raw_data.fins_raw import FichaInscripcionRaw
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType

class ParentsMapper:
    def __init__(self, registry: NormalizerRegistry):
        self.dni_normalizer:FieldNormalizer  = registry.get(DataType.DNI)
        self.name_normalizer:FieldNormalizer = registry.get(DataType.NAME)

    def map(self, fins_raw: FichaInscripcionRaw) -> ParentsData:
        if not fins_raw:
            return ParentsData()
            
        father = ParentDetail(
            dni=self.dni_normalizer.normalize(fins_raw.parents_father_dni),
            full_name=fins_raw.parents_father_full_name,
            phone=fins_raw.parents_father_phone
        )
        
        mother = ParentDetail(
            dni=self.dni_normalizer.normalize(fins_raw.parents_mother_dni),
            full_name=fins_raw.parents_mother_full_name,
            phone=fins_raw.parents_mother_phone
        )
        
        guardian = ParentDetail(
            dni=self.dni_normalizer.normalize(fins_raw.parents_guardian_dni),
            full_name=fins_raw.parents_guardian_full_name,
            phone=fins_raw.parents_guardian_phone
        )
        
        return ParentsData(
            father=father if father.dni or father.full_name else None,
            mother=mother if mother.dni or mother.full_name else None,
            guardian=guardian if guardian.dni or guardian.full_name else None
        )
