from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins
from src.contexts.data_quality_triage.domain.educa.value_objects.religion_data import ReligionData

class ReligionDomainMapper:
    def map(self, enriched_fins: EnrichedFins) -> ReligionData:
        return ReligionData(
            baptized=enriched_fins.religion.baptized.normalized_value,
            first_communion=enriched_fins.religion.first_communion.normalized_value
        )
