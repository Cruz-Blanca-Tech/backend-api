import re
from typing import Any
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData

class MedicalDomainMapper:
    @staticmethod
    def _is_empty_or_noise(val: Any) -> bool:
        if val is None:
            return True
        s = str(val).strip().lower()
        if not s:
            return True
        # Si solo contiene guiones, puntos, barras, espacios o puntuación típica de "no aplica"
        if re.sub(r'[\s\-_–—./,;~*]', '', s) == '':
            return True
        noise_tokens = {
            "selected", "unselected", "true", "false", "x", "yes", "no", "si", "sí",
            "ninguna", "ninguno", "ningun", "ningún", "nada", "n/a", "na", "no aplica",
            "none", "null", "no tiene", "sin", "no presenta", "-", "--", "---"
        }
        return s in noise_tokens

    def map(self, enriched_fins: EnrichedFins) -> MedicalData:
        m = enriched_fins.medical
        allergies = []
        if m.allergy_milk.normalized_value: allergies.append("Leche")
        if m.allergy_citrus.normalized_value: allergies.append("Cítricos")
        if m.allergy_penicillin.normalized_value: allergies.append("Penicilina")
        if m.allergy_sulfa_drugs.normalized_value: allergies.append("Sulfas")
        if m.allergy_fish_shellfish.normalized_value: allergies.append("Pescado / Mariscos")
        if m.allergy_nsaid_analgesics.normalized_value: allergies.append("Analgésicos (AINES)")
        
        # Si allergy_others contiene texto libre (no booleano ni ruido), se agrega como alergia
        other_all = m.allergy_others.normalized_value
        if other_all and isinstance(other_all, str) and not self._is_empty_or_noise(other_all):
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
        if other_ins and isinstance(other_ins, str) and not self._is_empty_or_noise(other_ins):
            insurance.append(other_ins.strip().title())

        vaccines = []
        if m.received_tetanus_vaccine.normalized_value: vaccines.append("Tétanos")

        medications = []
        med_name = (m.medication_name.normalized_value or "").strip() if isinstance(m.medication_name.normalized_value, str) else ""
        med_noise = {"recibio", "recibió", "recibioc", "recibióc"}
        if m.is_taking_medication.normalized_value and not self._is_empty_or_noise(med_name) and med_name.lower() not in med_noise:
            medications.append(med_name)

        op_reason = m.operation_reason.normalized_value
        if self._is_empty_or_noise(op_reason):
            op_reason = None
        else:
            op_reason = str(op_reason).strip()

        hosp_reason = m.hospitalization_reason.normalized_value
        if self._is_empty_or_noise(hosp_reason):
            hosp_reason = None
        else:
            hosp_reason = str(hosp_reason).strip()

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
