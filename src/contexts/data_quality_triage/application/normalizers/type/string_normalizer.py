from ..base import FieldNormalizer

class StringNormalizer(FieldNormalizer):
    def normalize(self, value: str) -> str:
        if value is None:
            return None
        return str(value).strip().lower()