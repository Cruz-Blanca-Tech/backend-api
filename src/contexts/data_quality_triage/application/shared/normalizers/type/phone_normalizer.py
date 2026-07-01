from typing import Any
from src.contexts.data_quality_triage.application.shared.normalizers.base.normalizer_strategy import NormalizerStrategy
from src.contexts.data_quality_triage.domain.shared.value_objects.phone_number import PhoneNumber

class PhoneNormalizer(NormalizerStrategy):
    def normalize(self, raw_value: Any) -> Any:
        if not raw_value:
            return None
            
        phone_str = str(raw_value).strip()
        # Optionally clean up weird OCR characters here if needed, e.g. removing extra spaces inside the string
        phone_str = phone_str.replace(" ", "")
        
        if PhoneNumber.is_valid(phone_str):
            return phone_str
            
        return raw_value # Return raw value so Triage engine can flag it as discrepancy
