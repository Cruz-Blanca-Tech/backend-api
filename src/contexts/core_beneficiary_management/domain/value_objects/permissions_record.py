from dataclasses import dataclass
from typing import Optional

@dataclass
class PermissionsRecord:
    haircut_permission: Optional[bool] = None
    medical_exams_permission: Optional[bool] = None
