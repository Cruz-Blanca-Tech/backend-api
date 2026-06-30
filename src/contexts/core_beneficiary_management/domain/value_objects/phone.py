from dataclasses import dataclass
import re

@dataclass(frozen=True)
class Phone:
    value: str

    def __post_init__(self):
        val = str(self.value).strip()
        if not val:
            raise ValueError("Phone cannot be empty")
        
        # Permit basic phone number formats (e.g., +51 987 654 321 or just 987654321)
        if not re.match(r"^\+?[0-9\s\-()]{7,20}$", val):
            raise ValueError(f"Invalid phone format: {val}")
        
        # We need to bypass frozen to set the normalized value
        object.__setattr__(self, 'value', val)

    def __str__(self) -> str:
        return self.value
