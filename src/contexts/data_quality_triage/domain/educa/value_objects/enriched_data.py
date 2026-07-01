from typing import List, Optional
from dataclasses import dataclass
from src.contexts.data_quality_triage.domain.shared.value_objects.enriched_field import EnrichedField

from src.contexts.data_quality_triage.domain.shared.value_objects.adult_role import AdultRole

@dataclass
class EnrichedAdult:
    role: AdultRole
    dni: EnrichedField
    first_name: EnrichedField
    last_name: EnrichedField
    phone: Optional[EnrichedField] = None

@dataclass
class EnrichedAddress:
    lot: EnrichedField
    block: EnrichedField
    city: EnrichedField
    district: EnrichedField
    neighborhood: EnrichedField

@dataclass
class EnrichedEducation:
    school: EnrichedField
    grade: EnrichedField
    knows_how_to_read: EnrichedField
    knows_how_to_write: EnrichedField
    has_repeated_grade: EnrichedField
    has_learning_difficulties: EnrichedField

@dataclass
class EnrichedMedical:
    has_been_hospitalized: EnrichedField
    hospitalization_reason: EnrichedField
    has_been_operated: EnrichedField
    operation_reason: EnrichedField
    has_complete_vaccines: EnrichedField
    received_tetanus_vaccine: EnrichedField
    is_taking_medication: EnrichedField
    medication_name: EnrichedField
    # Alergias
    allergy_milk: EnrichedField
    allergy_citrus: EnrichedField
    allergy_penicillin: EnrichedField
    allergy_sulfa_drugs: EnrichedField
    allergy_fish_shellfish: EnrichedField
    allergy_nsaid_analgesics: EnrichedField
    allergy_others: EnrichedField
    # Enfermedades
    disease_cancer: EnrichedField
    disease_seizures: EnrichedField
    disease_parasites: EnrichedField
    disease_chickenpox: EnrichedField
    disease_tuberculosis: EnrichedField
    # Seguros
    medical_insurance_sis: EnrichedField
    medical_insurance_essalud: EnrichedField
    medical_insurance_fospoli: EnrichedField
    medical_insurance_other: EnrichedField

@dataclass
class EnrichedReligion:
    baptized: EnrichedField
    first_communion: EnrichedField

@dataclass
class EnrichedPermissions:
    haircut: EnrichedField
    medical_exams: EnrichedField

@dataclass
class EnrichedFins:
    child_dni: EnrichedField
    child_first_name: EnrichedField
    child_last_name: EnrichedField
    child_birth_date: EnrichedField
    child_age: EnrichedField
    child_gender: EnrichedField
    adults: List[EnrichedAdult]
    emergency_contact_phone: EnrichedField
    address: EnrichedAddress
    education: EnrichedEducation
    medical: EnrichedMedical
    religion: EnrichedReligion
    permissions: EnrichedPermissions

@dataclass
class EnrichedDj:
    child_dni: EnrichedField
    guardian_dni: EnrichedField
