from typing import Any, Dict
from src.contexts.data_quality_triage.application.shared.services.normalize_registry import NormalizerRegistry
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType

from src.contexts.data_quality_triage.domain.educa.value_objects.raw_data.fins_raw import FichaInscripcionRaw

class MedicalMapper:
    def __init__(self, registry: NormalizerRegistry):
        self.bool_normalizer = registry.get(DataType.BOOL)

    def map(self, fins_raw: FichaInscripcionRaw) -> MedicalData:
        if not fins_raw:
            return MedicalData()
            
        # Alergias
        allergies = []
        allergy_checks = {
            "milk": fins_raw.allergy_milk,
            "citrus": fins_raw.allergy_citrus,
            "penicillin": fins_raw.allergy_penicillin,
            "sulfa_drugs": fins_raw.allergy_sulfa_drugs,
            "fish_shellfish": fins_raw.allergy_fish_shellfish,
            "nsaid_analgesics": fins_raw.allergy_nsaid_analgesics,
            "others": fins_raw.allergy_others
        }
        for key, value in allergy_checks.items():
            if self.bool_normalizer.normalize(value):
                allergies.append(key)
        
        other_details = fins_raw.allergy_other_details
        if other_details:
            allergies.append(f"other: {other_details}")
            
        # Enfermedades
        diseases = []
        disease_checks = {
            "cancer": fins_raw.disease_cancer,
            "seizures": fins_raw.disease_seizures,
            "parasites": fins_raw.disease_parasites,
            "chickenpox": fins_raw.disease_chickenpox,
            "tuberculosis": fins_raw.disease_tuberculosis
        }
        for key, value in disease_checks.items():
            if self.bool_normalizer.normalize(value):
                diseases.append(key)
                
        # Seguros
        insurance = []
        insurance_checks = {
            "sis": fins_raw.medical_insurance_sis,
            "essalud": fins_raw.medical_insurance_essalud,
            "fospoli": fins_raw.medical_insurance_fospoli,
            "other": fins_raw.medical_insurance_other
        }
        for key, value in insurance_checks.items():
            if self.bool_normalizer.normalize(value):
                insurance.append(key)
                
        # Hospitalizaciones / Operaciones
        has_been_hospitalized = self.bool_normalizer.normalize(fins_raw.medical_has_been_hospitalized) or fins_raw.medical_has_been_hospitalized not in (None, "NO", "unselected", "")
        
        return MedicalData(
            allergies=allergies,
            diseases=diseases,
            insurance=insurance,
            has_been_operated=self.bool_normalizer.normalize(fins_raw.medical_has_been_operated),
            operation_reason=fins_raw.medical_operation_reason,
            has_been_hospitalized=has_been_hospitalized,
            hospitalization_reason=fins_raw.medical_hospitalization_reason,
            has_complete_vaccines=self.bool_normalizer.normalize(fins_raw.medical_has_complete_vaccines),
            received_tetanus_vaccine=self.bool_normalizer.normalize(fins_raw.medical_received_tetanus_vaccine),
            is_taking_medication=self.bool_normalizer.normalize(fins_raw.medical_is_taking_medication),
            medication_name=fins_raw.medical_medication_name
        )
