from src.contexts.data_quality_triage.application.shared.mappers.base_enriched_mapper import BaseEnrichedMapper
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedReligion
from src.contexts.data_quality_triage.application.educa.dtos.raw.fins_raw import FinsRaw

class ReligionEnrichedMapper(BaseEnrichedMapper):
    def map(self, raw_dto: FinsRaw) -> EnrichedReligion:
        return EnrichedReligion(
            baptized=self.build_field(raw_dto.religion_baptized, "¿Fue bautizado?", DataType.BOOLEAN),
            first_communion=self.build_field(raw_dto.religion_first_communion, "¿Hizo la 1ra Comunión?", DataType.BOOLEAN)
        )
