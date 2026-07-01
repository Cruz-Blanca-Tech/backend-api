from typing import Optional, List
from pydantic import BaseModel, Field

class PermissionsSchema(BaseModel):
    haircut_permission: Optional[bool] = None
    medical_exams_permission: Optional[bool] = None
    validation_issues: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
