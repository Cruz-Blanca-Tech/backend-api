from typing import Optional, List
from pydantic import BaseModel, Field

class ReligionSchema(BaseModel):
    baptized: Optional[bool] = None
    first_communion: Optional[bool] = None
    validation_issues: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
