from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData

class MedicalDomainMapper:
    def map(self, enriched_fins: EnrichedFins) -> MedicalData:
        m = enriched_fins.medical
        allergies = []
        if m.allergy_milk.normalized_value: allergies.append("Leche")
        if m.allergy_citrus.normalized_value: allergies.append("Cítricos")
        if m.allergy_penicillin.normalized_value: allergies.append("Penicilina")
        if m.allergy_sulfa_drugs.normalized_value: allergies.append("Sulfas")
        if m.allergy_fish_shellfish.normalized_value: allergies.append("Pescado/Marisco")
        if m.allergy_nsaid_analgesics.normalized_value: allergies.append("AINES")
        if m.allergy_others.normalized_value: allergies.append("Otros")
            
        diseases = []
        if m.disease_cancer.normalized_value: diseases.append("Cáncer")
        if m.disease_seizures.normalized_value: diseases.append("Convulsiones")
        if m.disease_parasites.normalized_value: diseases.append("Parásitos")
        if m.disease_chickenpox.normalized_value: diseases.append("Varicela")
        if m.disease_tuberculosis.normalized_value: diseases.append("Tuberculosis")
            
        insurance = []
        if m.medical_insurance_sis.normalized_value: insurance.append("SIS")
        if m.medical_insurance_essalud.normalized_value: insurance.append("EsSalud")
        if m.medical_insurance_fospoli.normalized_value: insurance.append("Fospoli")
        if m.medical_insurance_other.normalized_value: insurance.append("Otro")

        return MedicalData(
            allergies=allergies,
            diseases=diseases,
            insurance=insurance,
            has_been_operated=m.has_been_operated.normalized_value or False,
            operation_reason=m.operation_reason.normalized_value,
            has_been_hospitalized=m.has_been_hospitalized.normalized_value or False,
            hospitalization_reason=m.hospitalization_reason.normalized_value,
            has_complete_vaccines=m.has_complete_vaccines.normalized_value or False,
            received_tetanus_vaccine=m.received_tetanus_vaccine.normalized_value or False,
            is_taking_medication=m.is_taking_medication.normalized_value or False,
            medication_name=m.medication_name.normalized_value
        )
