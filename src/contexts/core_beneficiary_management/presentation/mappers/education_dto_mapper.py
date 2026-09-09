from typing import Optional
from src.contexts.core_beneficiary_management.domain.value_objects.education_record import EducationRecord
from src.contexts.core_beneficiary_management.domain.value_objects.grade import Grade
from src.contexts.core_beneficiary_management.presentation.schemas.education_schemas import (
    EducationRecordResponse, EducationRecordPatchRequest, EducationRecordCreateRequest
)
import uuid

class EducationDtoMapper:
    @staticmethod
    def to_response(domain_entity: Optional[EducationRecord]) -> Optional[EducationRecordResponse]:
        if not domain_entity:
            return None
        return EducationRecordResponse(
            school=domain_entity.school,
            grade=domain_entity.grade.value if domain_entity.grade else None,
            knows_how_to_read=domain_entity.knows_how_to_read,
            knows_how_to_write=domain_entity.knows_how_to_write,
            has_repeated_grade=domain_entity.has_repeated_grade,
            has_learning_difficulties=domain_entity.has_learning_difficulties
        )

    @staticmethod
    def patch_domain(domain_entity: Optional[EducationRecord], patch_request: Optional[EducationRecordPatchRequest], beneficiary_id: uuid.UUID) -> Optional[EducationRecord]:
        if not patch_request:
            return domain_entity
            
        if not domain_entity:
            domain_entity = EducationRecord(id=uuid.uuid4(), beneficiary_id=beneficiary_id)
            
        update_data = patch_request.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "grade" and value is not None:
                setattr(domain_entity, field, Grade(value))
            else:
                setattr(domain_entity, field, value)
            
        return domain_entity

    @staticmethod
    def from_create_request(request: Optional[EducationRecordCreateRequest], beneficiary_id: uuid.UUID) -> Optional[EducationRecord]:
        if not request:
            return None
        grade_vo = None
        if request.grade:
            try:
                grade_vo = Grade(request.grade)
            except ValueError:
                grade_vo = None
        return EducationRecord(
            id=uuid.uuid4(),
            beneficiary_id=beneficiary_id,
            school=request.school,
            grade=grade_vo,
            knows_how_to_read=request.knows_how_to_read,
            knows_how_to_write=request.knows_how_to_write,
            has_repeated_grade=request.has_repeated_grade,
            has_learning_difficulties=request.has_learning_difficulties
        )

