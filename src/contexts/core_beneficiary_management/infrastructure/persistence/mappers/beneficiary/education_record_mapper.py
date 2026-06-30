from typing import Optional
from src.contexts.core_beneficiary_management.domain.value_objects.education_record import EducationRecord
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.education_record_model import EducationRecordModel

from src.contexts.core_beneficiary_management.domain.value_objects.grade import Grade

class EducationRecordMapper:
    @staticmethod
    def to_domain(model: Optional[EducationRecordModel]) -> Optional[EducationRecord]:
        if not model:
            return None
            
        grade = None
        if model.grade:
            try:
                grade = Grade(model.grade)
            except ValueError:
                pass

        return EducationRecord(
            id=model.id,
            beneficiary_id=model.beneficiary_id,
            school=model.school,
            grade=grade,
            knows_how_to_read=model.knows_how_to_read,
            knows_how_to_write=model.knows_how_to_write,
            has_repeated_grade=model.has_repeated_grade,
            has_learning_difficulties=model.has_learning_difficulties
        )

    @staticmethod
    def to_persistence(entity: Optional[EducationRecord], beneficiary_id) -> Optional[EducationRecordModel]:
        if not entity:
            return None
            
        return EducationRecordModel(
            id=entity.id,
            beneficiary_id=beneficiary_id,
            school=entity.school,
            grade=entity.grade.value if entity.grade else None,
            knows_how_to_read=entity.knows_how_to_read,
            knows_how_to_write=entity.knows_how_to_write,
            has_repeated_grade=entity.has_repeated_grade,
            has_learning_difficulties=entity.has_learning_difficulties
        )
