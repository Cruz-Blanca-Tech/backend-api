from typing import Optional
import uuid
from datetime import datetime

from src.contexts.core_beneficiary_management.application.shared.ports.dossier_processor_strategy import DossierProcessorStrategy
from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.application.dtos.educa_dossier_dto import EducaDossierDTO
from src.contexts.core_beneficiary_management.application.mappers.educa_dossier_mapper import EducaDossierMapper
from src.contexts.core_beneficiary_management.domain.value_objects.enrollment import Enrollment

class EducaDossierProcessor(DossierProcessorStrategy):
    
    def process(self, dossier_data: dict, existing_beneficiary: Optional[Beneficiary]) -> Beneficiary:
        # 1. Parse and validate using Pydantic DTO
        dto = EducaDossierDTO(**dossier_data)
        
        # 2. Map DTO to Domain Entity
        beneficiary = EducaDossierMapper.map_to_entity(dto, existing_beneficiary)

        # 3. Add Enrollment for EDUCA if it does not exist
        has_enrollment = any(e.activity_code == "EDUCA" for e in beneficiary.enrollments)
        if not has_enrollment:
            beneficiary.enrollments.append(Enrollment(
                id=uuid.uuid4(),
                beneficiary_id=beneficiary.id,
                activity_code="EDUCA",
                enrollment_date=datetime.utcnow().date()
            ))

        return beneficiary
