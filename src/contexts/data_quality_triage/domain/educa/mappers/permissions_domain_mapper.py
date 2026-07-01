from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins
from src.contexts.data_quality_triage.domain.educa.value_objects.permissions_data import PermissionsData

class PermissionsDomainMapper:
    def map(self, enriched_fins: EnrichedFins) -> PermissionsData:
        return PermissionsData(
            haircut_permission=enriched_fins.permissions.haircut.normalized_value,
            medical_exams_permission=enriched_fins.permissions.medical_exams.normalized_value
        )
