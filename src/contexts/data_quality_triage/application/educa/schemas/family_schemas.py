from typing import Optional, List
from pydantic import BaseModel, Field, model_validator

class RelatedAdultSchema(BaseModel):
    relationship: str
    dni: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True

class FamilySchema(BaseModel):
    adults: List[RelatedAdultSchema] = Field(default_factory=list)
    guardian_dni: Optional[str] = None
    emergency_contact_dni: Optional[str] = None
    validation_issues: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def apply_deduplication_and_rules(self) -> "FamilySchema":
        def normalize_role(raw_role: str) -> str:
            if not raw_role: return "OTHER"
            r_str = raw_role.upper()
            if r_str in ["MOTHER", "FATHER"]: return r_str
            return "OTHER"

        def is_same_person(a1: RelatedAdultSchema, a2_dni: Optional[str], a2_name: Optional[str]) -> bool:
            if a1.dni and a2_dni and a1.dni == a2_dni: return True
            if a1.full_name and a2_name and a1.full_name.lower() == a2_name.lower(): return True
            return False

        dedup_adults = []
        for a in self.adults:
            norm_role = normalize_role(a.relationship)
            raw_role = str(a.relationship).upper()
            
            existing = next((ex for ex in dedup_adults if is_same_person(ex, a.dni, a.full_name)), None)
            if existing:
                if existing.relationship == "OTHER" and norm_role in ["MOTHER", "FATHER"]:
                    existing.relationship = norm_role
                if not existing.dni and a.dni: existing.dni = a.dni
                if not existing.phone and a.phone: existing.phone = a.phone
                
                if raw_role in ["TUTOR", "APODERADO"] and not self.guardian_dni and existing.dni:
                    self.guardian_dni = existing.dni
            else:
                a.relationship = norm_role
                dedup_adults.append(a)
                if raw_role in ["TUTOR", "APODERADO"] and not self.guardian_dni and a.dni:
                    self.guardian_dni = a.dni
                    
        self.adults = dedup_adults
        return self
