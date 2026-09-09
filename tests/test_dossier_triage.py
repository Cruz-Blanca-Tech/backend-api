import pytest
from src.contexts.data_quality_triage.application.shared.factories.dossier_factory import DossierFactory
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType

RAW_PAYLOAD = {
    "beneficiary": {
        "dni": "78739850",
        "first_name": "SARAI MILENA",
        "last_name": "CHACON",
        "birth_date": "2021-06-28",
        "gender": "F"
    },
    "related_adults": {
        "adults": [
            {
                "relationship": "MOTHER",
                "dni": "48100010",
                "full_name": "MILAGROS VERONICA QUISPE",
                "phone": "999999999"
            }
        ],
        "guardian_dni": "48100010"
    },
    "education": {
        "school": "Colegio Nacional 123",
        "grade": "Primero Primaria",
        "knows_how_to_read": True,
        "knows_how_to_write": True,
        "has_repeated_grade": False,
        "has_learning_difficulties": True
    },
    "medical": {
        "has_been_hospitalized": True,
        "hospitalization_reason": "Problemas digestivos",
        "has_been_operated": False,
        "operation_reason": None,
        "vaccines": [],
        "medications": [],
        "allergies": ["Carne"],
        "diseases": [],
        "insurance": ["sis"]
    }
}

def test_dossier_factory_mapping_and_validation():
    inscription = DossierFactory.reconstitute(RAW_PAYLOAD, ActivityType.EDUCA_INSCRIPTION)
    
    # Assert Normalized DNI mappings
    assert inscription.beneficiary.dni == "78739850"
    assert inscription.related_adults.guardian_dni == "48100010"
    assert inscription.education.school == "Colegio Nacional 123"
    assert inscription.medical.has_been_hospitalized is True


def test_family_dni_uniqueness_duplicate_adults():
    import copy
    payload = copy.deepcopy(RAW_PAYLOAD)
    payload["related_adults"]["adults"] = [
        {"relationship": "FATHER", "dni": "10778773", "full_name": "CARLOS LOPEZ", "phone": "999888777"},
        {"relationship": "OTHER", "dni": "10778773", "full_name": "CARLOS LOPEZ JR", "phone": "999888777"},
    ]
    payload["related_adults"]["guardian_dni"] = "10778773"
    payload["related_adults"]["emergency_contact_dni"] = "10778773"

    dossier = DossierFactory.reconstitute(payload, ActivityType.EDUCA_INSCRIPTION)
    is_valid, issues = dossier.validate_completeness()

    dup_issues = [i for i in issues if "duplicado" in i.rule_description.lower()]
    assert len(dup_issues) == 1
    assert dup_issues[0].field_name == "related_adults.adults"
    assert dup_issues[0].actual_value == "10778773"
    assert is_valid is False


def test_family_dni_uniqueness_collision_with_beneficiary():
    import copy
    payload = copy.deepcopy(RAW_PAYLOAD)
    payload["beneficiary"]["dni"] = "78739850"
    payload["related_adults"]["adults"] = [
        {"relationship": "FATHER", "dni": "78739850", "full_name": "CARLOS LOPEZ", "phone": "999888777"},
    ]
    payload["related_adults"]["guardian_dni"] = "78739850"
    payload["related_adults"]["emergency_contact_dni"] = "78739850"

    dossier = DossierFactory.reconstitute(payload, ActivityType.EDUCA_INSCRIPTION)
    is_valid, issues = dossier.validate_completeness()

    collision_issues = [i for i in issues if "coincide con el del beneficiario" in i.rule_description.lower()]
    assert len(collision_issues) == 1
    assert collision_issues[0].field_name == "related_adults.adults"
    assert is_valid is False


def test_guardian_without_dni():
    import copy
    payload = copy.deepcopy(RAW_PAYLOAD)
    payload["related_adults"]["adults"] = [
        {"relationship": "MOTHER", "dni": "", "full_name": "MILAGROS VERONICA QUISPE", "phone": "999999999"}
    ]
    payload["related_adults"]["guardian_dni"] = None

    dossier = DossierFactory.reconstitute(payload, ActivityType.EDUCA_INSCRIPTION)
    is_valid, issues = dossier.validate_completeness()

    guardian_issues = [i for i in issues if i.field_name == "related_adults.guardian"]
    assert len(guardian_issues) >= 1
    assert "no cuenta con dni" in guardian_issues[0].rule_description.lower() or "no se ha asignado" in guardian_issues[0].rule_description.lower()
    assert is_valid is False


def test_adult_dni_with_letters_10722a():
    import copy
    payload = copy.deepcopy(RAW_PAYLOAD)
    payload["related_adults"]["adults"] = [
        {"relationship": "MOTHER", "dni": "10722a", "full_name": "MILAGROS VERONICA QUISPE", "phone": "999999999"}
    ]
    payload["related_adults"]["guardian_dni"] = "10722a"
    payload["related_adults"]["emergency_contact_dni"] = "10722a"

    dossier = DossierFactory.reconstitute(payload, ActivityType.EDUCA_INSCRIPTION)
    is_valid, issues = dossier.validate_completeness()

    format_issues = [i for i in issues if "8 dígitos numéricos" in i.rule_description]
    assert len(format_issues) >= 1
    # Should catch both adult DNI format and guardian DNI format
    adult_format_issue = next(i for i in issues if i.field_name == "related_adults.adults" and "10722a" in i.actual_value)
    assert adult_format_issue.severity == "ERROR"
    assert is_valid is False


def test_secondary_adult_without_dni():
    import copy
    payload = copy.deepcopy(RAW_PAYLOAD)
    # Mother is guardian with valid DNI, but Father has no DNI
    payload["related_adults"]["adults"] = [
        {"relationship": "MOTHER", "dni": "48100010", "full_name": "MILAGROS VERONICA QUISPE", "phone": "999999999"},
        {"relationship": "FATHER", "dni": "", "full_name": "CARLOS LOPEZ", "phone": "999888777"}
    ]
    payload["related_adults"]["guardian_dni"] = "48100010"
    payload["related_adults"]["emergency_contact_dni"] = "48100010"

    dossier = DossierFactory.reconstitute(payload, ActivityType.EDUCA_INSCRIPTION)
    is_valid, issues = dossier.validate_completeness()

    missing_dni_issues = [i for i in issues if "no tiene dni registrado" in i.rule_description.lower()]
    assert len(missing_dni_issues) == 1
    assert missing_dni_issues[0].severity == "ERROR"
    assert is_valid is False



