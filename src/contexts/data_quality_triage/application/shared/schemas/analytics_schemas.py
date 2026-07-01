from pydantic import BaseModel
from typing import Dict, List, Any

class TriageSummaryMetricsResponse(BaseModel):
    total_cases: int
    status_counts: Dict[str, int]
    global_average_confidence: float

class TopIssueResponse(BaseModel):
    field_name: str
    description: str
    count: int

class TriageIssuesResponse(BaseModel):
    top_issues: List[TopIssueResponse]
