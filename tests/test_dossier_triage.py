import pytest
from src.contexts.data_quality_triage.application.factories.dossier_factory import DossierFactory

RAW_DATA = {
    "FINS": {
        "child_first_name": "Soraia HJaman",
        "child_last_name": "Perez",
        "child_age": "5 años",
        "parents_mother_full_name": "Milagro Chacon quispe",
        "parents_father_full_name": "Ramiro Chacon",
        "parents_guardian_full_name": None,
        "education_school_name": "Colegio Nacional 123",
        "education_grade": "Primero Primaria",
        "education_knows_read": "selected",
        "education_knows_write": "si",
        "education_repeated_grade": "unselected",
        "education_learning_difficulties": "true",
        "medical_has_been_hospitalized": "selected",
        "medical_hospitalization_reason": "Problemas digestivos",
        "medical_has_been_operated": "no",
        "medical_allergies": ["other: Carne"],
        "medical_insurance": ["sis"]
    },
    "DNIBEF": {
        "FirstName": "SARAI MILENA",
        "LastName": "CHACON",
        "DocumentNumber": "78739850"
    },
    "DNIAP": {
        "FirstName": "MILAGROS VERONICA",
        "LastName": "QUISPE",
        "DocumentNumber": "4 8 1 00010 - 1"
    },
    "DJ": {
        "child_dni": "78739850",
        "parents_father_dni": "47 54 50 15",
        "parents_mother_dni": "4 8 1 00010"
    }
}

def test_dossier_factory_mapping_and_validation():
    inscription = DossierFactory.from_data(RAW_DATA)
    
    # Assert Normalized DNI mappings
    assert inscription.beneficiary.dni in (None, "")
    assert inscription.parents.mother.dni in (None, "")
    assert inscription.parents.father.dni in (None, "")

    # Assert Validation behavior
    phones = [p for p in [
        inscription.parents.father.phone if inscription.parents.father else None, 
        inscription.parents.mother.phone if inscription.parents.mother else None, 
        inscription.parents.guardian.phone if inscription.parents.guardian else None
    ] if p]
    
    if not phones:
        assert any("Debe existir al menos un número de emergencia" in issue for issue in inscription.parents.validation_issues)
    
    assert inscription.parents.apoderado_type is not None
