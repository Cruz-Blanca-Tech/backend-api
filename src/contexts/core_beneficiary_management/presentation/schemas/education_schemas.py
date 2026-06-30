from pydantic import BaseModel
from typing import Optional

class EducationRecordResponse(BaseModel):
    school: Optional[str]
    grade: Optional[str]
    knows_how_to_read: Optional[bool]
    knows_how_to_write: Optional[bool]
    has_repeated_grade: Optional[bool]
    has_learning_difficulties: Optional[bool]

class EducationRecordPatchRequest(BaseModel):
    school: Optional[str] = None
    grade: Optional[str] = None
    knows_how_to_read: Optional[bool] = None
    knows_how_to_write: Optional[bool] = None
    has_repeated_grade: Optional[bool] = None
    has_learning_difficulties: Optional[bool] = None
