from pydantic import BaseModel
from typing import Generic, TypeVar, List, Dict, Optional

T = TypeVar("T")

class DashboardResponse(BaseModel, Generic[T]):
    title: str
    description: str
    source: str
    legend: Optional[Dict[str, str]] = None
    data: List[T]
