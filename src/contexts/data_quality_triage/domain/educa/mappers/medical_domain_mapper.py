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
        if m.allergy_fish_shellfish.normalized_value: allergies.append("Pescado / Mariscos")
        if m.allergy_nsaid_analgesics.normalized_value: allergies.append("Analgésicos (AINES)")
        
        # Si allergy_others contiene texto libre (no booleano), se agrega como alergia
        other_all = m.allergy_others.normalized_value
        noise_tokens = {"selected", "unselected", "true", "false", "x", "yes", "no", "si", "sí", "ninguna", "ninguno"}
        if other_all and isinstance(other_all, str) and other_all.strip().lower() not in noise_tokens:
            allergies.append(other_all.strip().title())
            
        diseases = []
        if m.disease_cancer.normalized_value: diseases.append("Cáncer")
        if m.disease_seizures.normalized_value: diseases.append("Convulsiones")
        if m.disease_parasites.normalized_value: diseases.append("Parásitos")
        if m.disease_chickenpox.normalized_value: diseases.append("Varicela")
        if m.disease_tuberculosis.normalized_value: diseases.append("Tuberculosis")
            
        insurance = []
        if m.medical_insurance_sis.normalized_value: insurance.append("S.I.S.")
        if m.medical_insurance_essalud.normalized_value: insurance.append("ESSALUD")
        if m.medical_insurance_fospoli.normalized_value: insurance.append("FOSPOLI")
        
        other_ins = m.medical_insurance_other.normalized_value
        if other_ins:
            if isinstance(other_ins, str) and other_ins.strip().lower() not in noise_tokens:
                insurance.append(other_ins.strip().title())

        vaccines = []
        if m.received_tetanus_vaccine.normalized_value: vaccines.append("Tétanos")

        medications = []
        med_name = (m.medication_name.normalized_value or "").strip() if isinstance(m.medication_name.normalized_value, str) else ""
        med_noise = noise_tokens | {"recibio", "recibió", "recibioc", "recibióc"}
        if m.is_taking_medication.normalized_value and med_name and med_name.lower() not in med_noise:
            medications.append(med_name)

        op_reason = m.operation_reason.normalized_value
        if isinstance(op_reason, str) and op_reason.strip().lower() in noise_tokens:
            op_reason = None

        hosp_reason = m.hospitalization_reason.normalized_value
        if isinstance(hosp_reason, str) and hosp_reason.strip().lower() in noise_tokens:
            hosp_reason = None

        has_been_operated = bool(m.has_been_operated.normalized_value) or bool(op_reason)
        has_been_hospitalized = bool(m.has_been_hospitalized.normalized_value) or bool(hosp_reason)

        return MedicalData(
            allergies=allergies,
            diseases=diseases,
            insurance=insurance,
            has_been_operated=has_been_operated,
            operation_reason=op_reason,
            has_been_hospitalized=has_been_hospitalized,
            hospitalization_reason=hosp_reason,
            has_complete_vaccines=bool(m.has_complete_vaccines.normalized_value),
            vaccines=vaccines,
            medications=medications
        )
