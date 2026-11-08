"""D21: verificación de doble inscripción en la actividad del lote."""
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy


def unverified_enrollment_issue(dni) -> FieldDiscrepancy:
    """D21: error bloqueante cuando no se pudo comprobar la doble inscripción."""
    return FieldDiscrepancy(
        field_name="beneficiary.dni",
        expected_pattern="Inscripción verificada en la actividad del lote",
        actual_value=str(dni or ""),
        rule_description=(
            "No se pudo verificar si el niño ya está inscrito en la actividad del lote. "
            "Volvé a validar el expediente; si el error se repite, avisá al administrador."
        ),
        severity="ERROR",
        document_code="DOMINIO",
    )
