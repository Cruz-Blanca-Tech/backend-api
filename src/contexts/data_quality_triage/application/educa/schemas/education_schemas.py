from typing import Optional
from pydantic import BaseModel

class EducationSchema(BaseModel):
    school: Optional[str] = None
    grade: Optional[str] = None
    knows_read: bool = False
    knows_write: bool = False
    repeated_grade: bool = False
    learning_difficulties: bool = False

    class Config:
        from_attributes = True
