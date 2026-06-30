from dataclasses import dataclass
from datetime import date
from uuid import UUID

@dataclass
class Enrollment:
    id: UUID
    beneficiary_id: UUID
    activity_code: str
    enrollment_date: date
