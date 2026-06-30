from typing import Optional
from src.contexts.core_beneficiary_management.domain.value_objects.medical_record import MedicalRecord
from src.contexts.core_beneficiary_management.presentation.schemas.medical_schemas import MedicalRecordResponse, MedicalRecordPatchRequest
import uuid

class MedicalDtoMapper:
    @staticmethod
    def to_response(domain_entity: Optional[MedicalRecord]) -> Optional[MedicalRecordResponse]:
        if not domain_entity:
            return None
        return MedicalRecordResponse(
            has_been_hospitalized=domain_entity.has_been_hospitalized,
            hospitalization_reason=domain_entity.hospitalization_reason,
            has_been_operated=domain_entity.has_been_operated,
            operation_reason=domain_entity.operation_reason,
            vaccines=domain_entity.vaccines,
            medications=domain_entity.medications,
            allergies=domain_entity.allergies,
            diseases=domain_entity.diseases,
            insurance=domain_entity.insurance
        )

    @staticmethod
    def patch_domain(domain_entity: Optional[MedicalRecord], patch_request: Optional[MedicalRecordPatchRequest], beneficiary_id: uuid.UUID) -> Optional[MedicalRecord]:
        if not patch_request:
            return domain_entity
            
        if not domain_entity:
            domain_entity = MedicalRecord(
                id=uuid.uuid4(), 
                beneficiary_id=beneficiary_id,
                has_been_hospitalized=False,
                hospitalization_reason=None,
                has_been_operated=False,
                operation_reason=None,
                vaccines=[],
                medications=[],
                allergies=[],
                diseases=[],
                insurance=[]
            )
            
        for field, value in patch_request.dict(exclude_unset=True).items():
            setattr(domain_entity, field, value)
            
        return domain_entity
