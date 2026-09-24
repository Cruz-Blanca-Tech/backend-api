from typing import Optional
from pydantic import BaseModel

class EducationSchema(BaseModel):
    school: Optional[str] = None
    grade: Optional[str] = None
    knows_read: bool = True
    knows_write: bool = True
    repeated_grade: bool = False
    learning_difficulties: Optional[bool] = None
    validation_issues: list[str] = []

    class Config:
        from_attributes = True
