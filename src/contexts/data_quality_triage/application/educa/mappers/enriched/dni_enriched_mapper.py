from dataclasses import dataclass
from src.contexts.data_quality_triage.application.shared.mappers.base_enriched_mapper import BaseEnrichedMapper
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.domain.shared.value_objects.enriched_field import EnrichedField
from src.contexts.data_quality_triage.application.educa.dtos.raw.dni_raw import DniRaw

@dataclass
class EnrichedDni:
    document_number: EnrichedField
    first_name: EnrichedField
    last_name: EnrichedField
    date_of_birth: EnrichedField

class DniEnrichedMapper(BaseEnrichedMapper):
    def map(self, raw_dto: DniRaw) -> EnrichedDni:
        return EnrichedDni(
            document_number=self.build_field(raw_dto.document_number, "Número de Documento", DataType.DNI),
            first_name=self.build_field(raw_dto.first_name, "Nombres", DataType.NAME),
            last_name=self.build_field(raw_dto.last_name, "Apellidos", DataType.NAME),
            date_of_birth=self.build_field(raw_dto.date_of_birth, "Fecha de Nacimiento", DataType.DATE)
        )
