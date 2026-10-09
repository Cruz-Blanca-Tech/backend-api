"""Tests para el mapeo de llaves de FINS, normalización médica y reglas opcionales de motivos."""
from src.contexts.data_quality_triage.application.educa.dtos.raw.fins_raw import FinsRaw
from src.contexts.data_quality_triage.application.educa.mappers.enriched.fins_enriched_mapper import (
    FinsEnrichedMapper,
)
from src.contexts.data_quality_triage.application.shared.services.normalize_registry import (
    NormalizerRegistry,
)
from src.contexts.data_quality_triage.domain.educa.mappers.educa_inscription_domain_mapper import (
    EducaInscriptionDomainMapper,
)
from src.contexts.data_quality_triage.domain.educa.rules.domain.medical_rules import (
    MedicalRules,
)


def _map_fins_to_domain(raw_dict: dict):
    fins = FinsRaw.from_dict(raw_dict)
    registry = NormalizerRegistry()
    enriched_fins = FinsEnrichedMapper(registry).map(fins)
    domain_dossier = EducaInscriptionDomainMapper().map(enriched_fins)
    return fins, domain_dossier


def test_fins_raw_maps_azure_general_and_checkbox_keys():
    raw_dict = {
        "general_is_baptized": "SI",
        "general_has_first_communion": "NO.",
        "general_can_cut_hair": "SI",
        "general_can_take_medical_exams": "NO",
        "general_emergency_phone": "987654321",
        "educational_knows_how_to_read_yes": "unselected",
        "educational_knows_how_to_read_no": "selected",
        "educational_knows_how_to_write_yes": "unselected",
        "educational_knows_how_to_write_no": "unselected",
        "educational_has_repeated_grade_yes": "selected",
        "educational_has_repeated_grade_no": "unselected",
        "allergy_others": "selected",
        "allergy_other_details": "Polen y polvo",
        "medical_operation_reason": "Apendicitis",
        "medical_hospitalization_reason": "Observación post operatoria",
        "medical_is_taking_medication": "SI",
        "medical_medication_name": "recibió",
    }

    fins, domain = _map_fins_to_domain(raw_dict)
    assert fins.religion_baptized == "SI"
    assert fins.religion_first_communion == "NO."
    assert fins.permission_haircut == "SI"
    assert fins.permission_medical_exams == "NO"
    assert fins.parents_emergency_contact_phone == "987654321"
    assert fins.educational_knows_how_to_read_yes == "NO"
    assert fins.educational_knows_how_to_write_yes is None
    assert fins.educational_has_repeated_grade_yes == "SI"
    assert fins.allergy_others == "Polen y polvo"

    # Religión y permisos
    assert domain.religion.baptized is True
    assert domain.religion.first_communion is False
    assert domain.permissions.haircut_permission is True
    assert domain.permissions.medical_exams_permission is False

    # Educación: _no marcado -> False; ambos desmarcados -> None (default True en knows_write); _yes marcado -> True
    assert domain.education.knows_read is False
    assert domain.education.knows_write is True
    assert domain.education.repeated_grade is True

    # Salud: allergy_others se incorpora a allergies, y los motivos activan el flag booleano
    assert "Polen Y Polvo" in domain.medical.allergies
    assert domain.medical.has_been_operated is True
    assert domain.medical.operation_reason == "apendicitis"
    assert domain.medical.has_been_hospitalized is True
    assert domain.medical.hospitalization_reason == "observación post operatoria"
    # Ruido OCR filtrado en medication_name
    assert domain.medical.medications == []


def test_hospitalization_and_operation_reasons_are_optional():
    _, domain = _map_fins_to_domain(
        {
            "medical_has_been_operated": "SI",
            "medical_operation_reason": None,
            "medical_has_been_hospitalized": "SI",
            "medical_hospitalization_reason": None,
        }
    )

    assert domain.medical.has_been_operated is True
    assert domain.medical.has_been_hospitalized is True
    assert MedicalRules().evaluate(domain) == []


def test_operation_and_hospitalization_dash_reason_is_treated_as_none():
    _, domain = _map_fins_to_domain(
        {
            "medical_has_been_operated": "NO",
            "medical_operation_reason": "-",
            "medical_has_been_hospitalized": "NO",
            "medical_hospitalization_reason": "--",
        }
    )

    assert domain.medical.has_been_operated is False
    assert domain.medical.operation_reason is None
    assert domain.medical.has_been_hospitalized is False
    assert domain.medical.hospitalization_reason is None
