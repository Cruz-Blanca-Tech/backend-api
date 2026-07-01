from dataclasses import dataclass
from typing import Optional

@dataclass
class ReligionRecord:
    baptized: Optional[bool] = None
    first_communion: Optional[bool] = None
