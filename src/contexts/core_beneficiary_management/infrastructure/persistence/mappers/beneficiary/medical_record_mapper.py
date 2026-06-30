from typing import Optional
from src.contexts.core_beneficiary_management.domain.value_objects.medical_record import MedicalRecord
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.medical_record_model import MedicalRecordModel

class MedicalRecordMapper:
    @staticmethod
    def to_domain(model: Optional[MedicalRecordModel]) -> Optional[MedicalRecord]:
        if not model:
            return None
            
        return MedicalRecord(
            id=model.id,
            beneficiary_id=model.beneficiary_id,
            has_been_hospitalized=model.has_been_hospitalized,
            hospitalization_reason=model.hospitalization_reason,
            has_been_operated=model.has_been_operated,
            operation_reason=model.operation_reason,
            vaccines=model.vaccines,
            medications=model.medications,
            allergies=model.allergies,
            diseases=model.diseases,
            insurance=model.insurance
        )

    @staticmethod
    def to_persistence(entity: Optional[MedicalRecord], beneficiary_id) -> Optional[MedicalRecordModel]:
        if not entity:
            return None
            
        return MedicalRecordModel(
            id=entity.id,
            beneficiary_id=beneficiary_id,
            has_been_hospitalized=entity.has_been_hospitalized,
            hospitalization_reason=entity.hospitalization_reason,
            has_been_operated=entity.has_been_operated,
            operation_reason=entity.operation_reason,
            vaccines=entity.vaccines,
            medications=entity.medications,
            allergies=entity.allergies,
            diseases=entity.diseases,
            insurance=entity.insurance
        )
