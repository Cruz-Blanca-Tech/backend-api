from typing import Any, Dict

from src.contexts.data_quality_triage.application.shared.services.normalize_registry import NormalizerRegistry
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData
from src.contexts.data_quality_triage.domain.educa.value_objects.raw_data.fins_raw import FichaInscripcionRaw
from src.contexts.data_quality_triage.application.educa.mappers import (
    BeneficiaryMapper, ParentsMapper, EducationMapper, MedicalMapper
)

class EducaInscriptionMapper:
    def __init__(self, registry: NormalizerRegistry = None):
        self.registry = registry or NormalizerRegistry()
        self.beneficiary_mapper = BeneficiaryMapper(self.registry)
        self.parents_mapper = ParentsMapper(self.registry)
        self.education_mapper = EducationMapper(self.registry)
        self.medical_mapper = MedicalMapper(self.registry)

    def map_beneficiary(self, fins_raw: FichaInscripcionRaw) -> BeneficiaryData:
        return self.beneficiary_mapper.map(fins_raw)

    def map_parents(self, fins_raw: FichaInscripcionRaw) -> FamilyData:
        return self.parents_mapper.map(fins_raw)

    def map_education(self, fins_raw: FichaInscripcionRaw) -> EducationData:
        return self.education_mapper.map(fins_raw)

    def map_medical(self, fins_raw: FichaInscripcionRaw) -> MedicalData:
        return self.medical_mapper.map(fins_raw)
