from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData

class BeneficiaryDomainMapper:
    def map(self, enriched_fins: EnrichedFins) -> BeneficiaryData:
        return BeneficiaryData(
            first_name=enriched_fins.child_first_name.normalized_value,
            last_name=enriched_fins.child_last_name.normalized_value,
            dni=enriched_fins.child_dni.normalized_value,
            birth_date=enriched_fins.child_birth_date.normalized_value,
            gender=enriched_fins.child_gender.normalized_value
        )
