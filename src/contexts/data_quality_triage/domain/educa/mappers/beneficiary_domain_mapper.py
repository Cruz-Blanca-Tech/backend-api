from typing import Any
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData

class BeneficiaryDomainMapper:
    def map(self, enriched_fins: EnrichedFins, enriched_dnibe: Any = None) -> BeneficiaryData:
        # Default to FINS
        first_name = enriched_fins.child_first_name.normalized_value if enriched_fins.child_first_name else None
        last_name = enriched_fins.child_last_name.normalized_value if enriched_fins.child_last_name else None
        dni = enriched_fins.child_dni.normalized_value if enriched_fins.child_dni else None
        
        # Override with DNI si está presente (es mucho más confiable que el texto a mano de FINS)
        if enriched_dnibe:
            if enriched_dnibe.first_name and enriched_dnibe.first_name.normalized_value:
                first_name = enriched_dnibe.first_name.normalized_value
            if enriched_dnibe.last_name and enriched_dnibe.last_name.normalized_value:
                last_name = enriched_dnibe.last_name.normalized_value
            if enriched_dnibe.document_number and enriched_dnibe.document_number.normalized_value:
                dni = enriched_dnibe.document_number.normalized_value

        return BeneficiaryData(
            first_name=first_name,
            last_name=last_name,
            dni=dni,
            birth_date=enriched_fins.child_birth_date.normalized_value if enriched_fins.child_birth_date else None,
            gender=enriched_fins.child_gender.normalized_value if enriched_fins.child_gender else None,
            age=enriched_fins.child_age.normalized_value if enriched_fins.child_age else None
        )
