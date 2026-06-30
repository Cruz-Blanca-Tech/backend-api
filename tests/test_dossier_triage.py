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
