from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class ReligionData:
    baptized: Optional[bool] = None
    first_communion: Optional[bool] = None
    validation_issues: List[str] = field(default_factory=list)
