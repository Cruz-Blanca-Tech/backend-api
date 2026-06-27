from ..base import FieldNormalizer

class DniNormalizer(FieldNormalizer):
    def normalize(self, value):
        if not value:
            return ""
        val_str = str(value).strip()
        if not val_str:
            return ""
        
        if "-" in val_str:
            parts = val_str.split("-")
            first_part_digits = "".join(c for c in parts[0] if c.isdigit())
            if len(first_part_digits) == 8:
                return first_part_digits
        
        digits = "".join(c for c in val_str if c.isdigit())
        if len(digits) > 8:
            return digits[:8]
        return digits
