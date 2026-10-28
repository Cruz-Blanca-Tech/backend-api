from typing import Optional, Any
from pydantic import BaseModel, model_validator

class EducationSchema(BaseModel):
    school: Optional[str] = None
    grade: Optional[str] = None
    knows_read: bool = True
    knows_write: bool = True
    repeated_grade: bool = False
    learning_difficulties: Optional[bool] = None
    validation_issues: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def map_alternate_education_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "knows_how_to_read" in data and "knows_read" not in data:
                val = data.get("knows_how_to_read")
                data["knows_read"] = bool(val) if val is not None else True
            if "knows_how_to_write" in data and "knows_write" not in data:
                val = data.get("knows_how_to_write")
                data["knows_write"] = bool(val) if val is not None else True
            if "has_repeated_grade" in data and "repeated_grade" not in data:
                val = data.get("has_repeated_grade")
                data["repeated_grade"] = bool(val) if val is not None else False
            if "has_learning_difficulties" in data and "learning_difficulties" not in data:
                val = data.get("has_learning_difficulties")
                data["learning_difficulties"] = bool(val) if val is not None else None
        return data

    class Config:
        from_attributes = True
