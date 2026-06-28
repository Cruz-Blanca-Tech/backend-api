from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class MedicalData:
    allergies: List[str] = field(default_factory=list)
    diseases: List[str] = field(default_factory=list)
    insurance: List[str] = field(default_factory=list)
    has_been_operated: bool = False
    operation_reason: Optional[str] = None
    has_been_hospitalized: bool = False
    hospitalization_reason: Optional[str] = None
    has_complete_vaccines: bool = False
    received_tetanus_vaccine: bool = False
    is_taking_medication: bool = False
    medication_name: Optional[str] = None


