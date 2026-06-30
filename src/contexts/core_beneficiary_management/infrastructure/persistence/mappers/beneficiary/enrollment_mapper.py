from typing import Optional
from src.contexts.core_beneficiary_management.domain.value_objects.enrollment import Enrollment
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.enrollment_model import EnrollmentModel

class EnrollmentMapper:
    @staticmethod
    def to_domain(model: Optional[EnrollmentModel]) -> Optional[Enrollment]:
        if not model:
            return None
            
        return Enrollment(
            id=model.id,
            beneficiary_id=model.beneficiary_id,
            activity_code=model.activity_code,
            enrollment_date=model.enrollment_date
        )

    @staticmethod
    def to_persistence(entity: Optional[Enrollment], beneficiary_id) -> Optional[EnrollmentModel]:
        if not entity:
            return None
            
        return EnrollmentModel(
            id=entity.id,
            beneficiary_id=beneficiary_id,
            activity_code=entity.activity_code,
            enrollment_date=entity.enrollment_date
        )
