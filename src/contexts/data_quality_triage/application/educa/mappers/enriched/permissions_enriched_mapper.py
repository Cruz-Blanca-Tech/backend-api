from src.contexts.data_quality_triage.application.shared.mappers.base_enriched_mapper import BaseEnrichedMapper
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedPermissions
from src.contexts.data_quality_triage.application.educa.dtos.raw.fins_raw import FinsRaw

class PermissionsEnrichedMapper(BaseEnrichedMapper):
    def map(self, raw_dto: FinsRaw) -> EnrichedPermissions:
        return EnrichedPermissions(
            haircut=self.build_field(raw_dto.permission_haircut, "¿Podemos cortarle el pelo?", DataType.BOOLEAN),
            medical_exams=self.build_field(raw_dto.permission_medical_exams, "¿Podemos hacerle exámenes médicos?", DataType.BOOLEAN)
        )
