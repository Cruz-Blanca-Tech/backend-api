from src.contexts.data_quality_triage.application.shared.mappers.base_enriched_mapper import BaseEnrichedMapper
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedDj
from src.contexts.data_quality_triage.application.educa.dtos.raw.dj_raw import DjRaw

class DjEnrichedMapper(BaseEnrichedMapper):
    def map(self, raw_dto: DjRaw) -> EnrichedDj:
        return EnrichedDj(
            child_dni=self.build_field(raw_dto.child_dni, "DNI Niño", DataType.DNI),
            guardian_dni=self.build_field(raw_dto.guardian_dni, "DNI Apoderado", DataType.DNI)
        )
