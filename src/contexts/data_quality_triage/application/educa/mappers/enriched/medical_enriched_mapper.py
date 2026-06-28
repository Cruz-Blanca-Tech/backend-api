from src.contexts.data_quality_triage.application.shared.mappers.base_enriched_mapper import BaseEnrichedMapper
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedMedical
from src.contexts.data_quality_triage.application.educa.dtos.raw.fins_raw import FinsRaw

class MedicalEnrichedMapper(BaseEnrichedMapper):
    def map(self, raw_dto: FinsRaw) -> EnrichedMedical:
        return EnrichedMedical(
            has_been_hospitalized=self.build_field(raw_dto.medical_has_been_hospitalized, "¿Hospitalizado?", DataType.BOOL),
            hospitalization_reason=self.build_field(raw_dto.medical_hospitalization_reason, "Motivo Hospitalización", DataType.STRING),
            has_been_operated=self.build_field(raw_dto.medical_has_been_operated, "¿Operado?", DataType.BOOL),
            operation_reason=self.build_field(raw_dto.medical_operation_reason, "Motivo Operación", DataType.STRING),
            has_complete_vaccines=self.build_field(raw_dto.medical_has_complete_vaccines, "Vacunas Completas", DataType.BOOL),
            received_tetanus_vaccine=self.build_field(raw_dto.medical_received_tetanus_vaccine, "Vacuna Tétanos", DataType.BOOL),
            is_taking_medication=self.build_field(raw_dto.medical_is_taking_medication, "Toma medicamentos", DataType.BOOL),
            medication_name=self.build_field(raw_dto.medical_medication_name, "Nombre Medicamento", DataType.STRING),
            # Alergias
            allergy_milk=self.build_field(raw_dto.allergy_milk, "Alergia Leche", DataType.BOOL),
            allergy_citrus=self.build_field(raw_dto.allergy_citrus, "Alergia Cítricos", DataType.BOOL),
            allergy_penicillin=self.build_field(raw_dto.allergy_penicillin, "Alergia Penicilina", DataType.BOOL),
            allergy_sulfa_drugs=self.build_field(raw_dto.allergy_sulfa_drugs, "Alergia Sulfas", DataType.BOOL),
            allergy_fish_shellfish=self.build_field(raw_dto.allergy_fish_shellfish, "Alergia Pescado/Marisco", DataType.BOOL),
            allergy_nsaid_analgesics=self.build_field(raw_dto.allergy_nsaid_analgesics, "Alergia AINES", DataType.BOOL),
            allergy_others=self.build_field(raw_dto.allergy_others, "Otras Alergias", DataType.BOOL),
            # Enfermedades
            disease_cancer=self.build_field(raw_dto.disease_cancer, "Cáncer", DataType.BOOL),
            disease_seizures=self.build_field(raw_dto.disease_seizures, "Convulsiones", DataType.BOOL),
            disease_parasites=self.build_field(raw_dto.disease_parasites, "Parásitos", DataType.BOOL),
            disease_chickenpox=self.build_field(raw_dto.disease_chickenpox, "Varicela", DataType.BOOL),
            disease_tuberculosis=self.build_field(raw_dto.disease_tuberculosis, "Tuberculosis", DataType.BOOL),
            # Seguros
            medical_insurance_sis=self.build_field(raw_dto.medical_insurance_sis, "SIS", DataType.BOOL),
            medical_insurance_essalud=self.build_field(raw_dto.medical_insurance_essalud, "EsSalud", DataType.BOOL),
            medical_insurance_fospoli=self.build_field(raw_dto.medical_insurance_fospoli, "Fospoli", DataType.BOOL),
            medical_insurance_other=self.build_field(raw_dto.medical_insurance_other, "Otro Seguro", DataType.BOOL)
        )
