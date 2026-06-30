from dataclasses import dataclass
import re

@dataclass(frozen=True)
class DNI:
    value: str

    def __post_init__(self):
        val = str(self.value).strip().upper()
        # Remove hyphens common in Peruvian DNI formats (e.g. 12345678-1)
        val = val.replace("-", "")
        
        if not val:
            raise ValueError("DNI/ID cannot be empty")
        
        # Permit letters and numbers, max 20 chars (for foreign IDs)
        if not re.match(r"^[A-Z0-9]{5,20}$", val):
            raise ValueError(f"Invalid DNI/ID format: {val}. Must be alphanumeric and 5-20 characters.")
        
        # We need to bypass frozen to set the normalized value
        object.__setattr__(self, 'value', val)

    def __str__(self) -> str:
        return self.value
