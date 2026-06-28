from typing import Dict, Any
from pydantic import BaseModel

class TriageCorrectionRequest(BaseModel):
    corrected_fields: Dict[str, Dict[str, Any]]

class TriageRejectRequest(BaseModel):
    reason: str
