from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional
from uuid import UUID

@dataclass
class MedicalRecord:
    id: UUID
    beneficiary_id: UUID
    has_been_hospitalized: bool
    hospitalization_reason: Optional[str]
    has_been_operated: bool
    operation_reason: Optional[str]
    vaccines: List[str]
    medications: List[str]
    allergies: List[str]
    diseases: List[str]
    insurance: List[str]

@dataclass
class EducationRecord:
    id: UUID
    beneficiary_id: UUID
    school: Optional[str]
    grade: Optional[str]
    knows_how_to_read: bool
    knows_how_to_write: bool
    has_repeated_grade: bool
    has_learning_difficulties: bool

@dataclass
class Relative:
    id: UUID
    beneficiary_id: UUID
    dni: str
    full_name: str
    role: str
    phone: Optional[str]

@dataclass
class HistoricalDocument:
    id: UUID
    beneficiary_id: UUID
    document_type: str
    year: int
    file_url: str

@dataclass
class Enrollment:
    id: UUID
    beneficiary_id: UUID
    activity_code: str
    enrollment_date: date

@dataclass
class Beneficiary:
    id: UUID
    dni: str
    first_name: str
    last_name: str
    birth_date: date
    gender: str
    medical_record: Optional[MedicalRecord] = None
    education_record: Optional[EducationRecord] = None
    relatives: List[Relative] = field(default_factory=list)
    historical_documents: List[HistoricalDocument] = field(default_factory=list)
    enrollments: List[Enrollment] = field(default_factory=list)

