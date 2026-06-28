from src.contexts.data_quality_triage.application.shared.mappers.base_enriched_mapper import BaseEnrichedMapper
from src.contexts.data_quality_triage.application.shared.services.normalize_registry import NormalizerRegistry
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins
from src.contexts.data_quality_triage.application.educa.dtos.raw.fins_raw import FinsRaw

from .address_enriched_mapper import AddressEnrichedMapper
from .education_enriched_mapper import EducationEnrichedMapper
from .medical_enriched_mapper import MedicalEnrichedMapper
from .adults_enriched_mapper import AdultsEnrichedMapper

class FinsEnrichedMapper(BaseEnrichedMapper):
    def __init__(self, registry: NormalizerRegistry):
        super().__init__(registry)
        self.address_mapper = AddressEnrichedMapper(registry)
        self.education_mapper = EducationEnrichedMapper(registry)
        self.medical_mapper = MedicalEnrichedMapper(registry)
        self.adults_mapper = AdultsEnrichedMapper(registry)

    def map(self, raw_dto: FinsRaw) -> EnrichedFins:
        return EnrichedFins(
            child_dni=self.build_field(raw_dto.child_dni, "DNI del Niño/a", DataType.DNI),
            child_first_name=self.build_field(raw_dto.child_first_name, "Nombres", DataType.NAME),
            child_last_name=self.build_field(raw_dto.child_last_name, "Apellidos", DataType.NAME),
            child_birth_date=self.build_field(raw_dto.child_birth_date, "Fecha de Nacimiento", DataType.DATE),
            child_age=self.build_field(raw_dto.child_age, "Edad", DataType.INT),
            child_gender=self.build_field(raw_dto.child_gender, "Sexo", DataType.GENDER),
            adults=self.adults_mapper.map(raw_dto),
            address=self.address_mapper.map(raw_dto),
            education=self.education_mapper.map(raw_dto),
            medical=self.medical_mapper.map(raw_dto)
        )
