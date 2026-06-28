from typing import List, Tuple, Any
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy

def validate_exact_match(
    fields_to_check: List[Tuple[str, Any]], 
    field_name: str, 
    rule_description: str,
    expected_pattern: str = "Los valores deben coincidir exactamente en todos los documentos"
) -> List[FieldDiscrepancy]:
    """
    Valida que todos los EnrichedFields en la lista proporcionada sean exactamente iguales.
    fields_to_check: Lista de tuplas (codigo_documento, EnrichedField)
    """
    valid_values = {}
    for doc_code, enriched_field in fields_to_check:
        if enriched_field and enriched_field.is_valid and enriched_field.normalized_value:
            valid_values[doc_code] = str(enriched_field.normalized_value)

    if len(valid_values) > 1 and len(set(valid_values.values())) > 1:
        mismatches = ", ".join([f"{k}: {v}" for k, v in valid_values.items()])
        return [FieldDiscrepancy(
            field_name=field_name, 
            expected_pattern=expected_pattern,
            actual_value=mismatches,
            rule_description=rule_description, 
            severity="WARNING", 
            document_code="CROSS_CHECK"
        )]
    return []
