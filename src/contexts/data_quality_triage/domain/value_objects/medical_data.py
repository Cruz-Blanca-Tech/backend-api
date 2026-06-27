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

    def to_dict(self) -> dict:
        return {
            "allergies": self.allergies,
            "diseases": self.diseases,
            "insurance": self.insurance,
            "has_been_operated": self.has_been_operated,
            "operation_reason": self.operation_reason,
            "has_been_hospitalized": self.has_been_hospitalized,
            "hospitalization_reason": self.hospitalization_reason,
            "has_complete_vaccines": self.has_complete_vaccines,
            "received_tetanus_vaccine": self.received_tetanus_vaccine,
            "is_taking_medication": self.is_taking_medication,
            "medication_name": self.medication_name
        }
