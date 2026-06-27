from typing import Optional, List
from pydantic import BaseModel, Field

class FichaInscripcionRaw(BaseModel):
    """Representa el payload crudo extraído de la Ficha de Inscripción (FINS)"""
    # Beneficiary info
    child_first_name: Optional[str] = None
    child_last_name: Optional[str] = None
    child_age: Optional[str] = None
    child_gender: Optional[str] = None
    child_birth_date: Optional[str] = None
    child_dni: Optional[str] = None

    # Parents / Apoderado info
    parents_father_full_name: Optional[str] = None
    parents_father_phone: Optional[str] = None
    parents_father_dni: Optional[str] = None
    parents_mother_full_name: Optional[str] = None
    parents_mother_phone: Optional[str] = None
    parents_mother_dni: Optional[str] = None
    parents_guardian_full_name: Optional[str] = None
    parents_guardian_phone: Optional[str] = None
    parents_guardian_dni: Optional[str] = None

    # Education info
    child_school: Optional[str] = None
    child_grade: Optional[str] = None
    educational_knows_how_to_read_yes: Optional[str] = None
    educational_knows_how_to_write_yes: Optional[str] = None
    educational_has_repeated_grade_yes: Optional[str] = None
    educational_has_learning_difficulties_yes: Optional[str] = None

    # Medical info
    allergy_milk: Optional[str] = None
    allergy_citrus: Optional[str] = None
    allergy_penicillin: Optional[str] = None
    allergy_sulfa_drugs: Optional[str] = None
    allergy_fish_shellfish: Optional[str] = None
    allergy_nsaid_analgesics: Optional[str] = None
    allergy_others: Optional[str] = None
    allergy_other_details: Optional[str] = None

    disease_cancer: Optional[str] = None
    disease_seizures: Optional[str] = None
    disease_parasites: Optional[str] = None
    disease_chickenpox: Optional[str] = None
    disease_tuberculosis: Optional[str] = None

    medical_insurance_sis: Optional[str] = None
    medical_insurance_essalud: Optional[str] = None
    medical_insurance_fospoli: Optional[str] = None
    medical_insurance_other: Optional[str] = None

    medical_has_been_hospitalized: Optional[str] = None
    medical_hospitalization_reason: Optional[str] = None
    medical_has_been_operated: Optional[str] = None
    medical_operation_reason: Optional[str] = None
    medical_has_complete_vaccines: Optional[str] = None
    medical_received_tetanus_vaccine: Optional[str] = None
    medical_is_taking_medication: Optional[str] = None
    medical_medication_name: Optional[str] = None
