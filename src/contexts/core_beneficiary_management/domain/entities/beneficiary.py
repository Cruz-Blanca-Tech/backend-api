from dataclasses import dataclass, field
from typing import List, Optional

from src.contexts.core_beneficiary_management.domain.entities.person import Person
from src.contexts.core_beneficiary_management.domain.value_objects.medical_record import MedicalRecord
from src.contexts.core_beneficiary_management.domain.value_objects.education_record import EducationRecord
from src.contexts.core_beneficiary_management.domain.value_objects.historical_document import HistoricalDocument
from src.contexts.core_beneficiary_management.domain.value_objects.enrollment import Enrollment
from src.contexts.core_beneficiary_management.domain.value_objects.religion_record import ReligionRecord
from src.contexts.core_beneficiary_management.domain.value_objects.permissions_record import PermissionsRecord

@dataclass
class Beneficiary(Person):
    religion_record: Optional[ReligionRecord] = None
    permissions_record: Optional[PermissionsRecord] = None
    medical_record: Optional[MedicalRecord] = None
    education_record: Optional[EducationRecord] = None
    # We store the adults (relatives) related to this beneficiary here
    relatives: List["Adult"] = field(default_factory=list)
    historical_documents: List[HistoricalDocument] = field(default_factory=list)
    enrollments: List[Enrollment] = field(default_factory=list)

    def __post_init__(self):
        self.type = "beneficiary"
