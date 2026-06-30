from dataclasses import dataclass
import re

@dataclass(frozen=True)
class Grade:
    value: str

    def __post_init__(self):
        val = str(self.value).strip().upper()
        if not val:
            raise ValueError("Grade cannot be empty")
        
        # Max 100 characters just to ensure no arbitrary large string is inserted
        if len(val) > 100:
            raise ValueError(f"Grade is too long: max 100 chars")
        
        object.__setattr__(self, 'value', val)

    def __str__(self) -> str:
        return self.value
