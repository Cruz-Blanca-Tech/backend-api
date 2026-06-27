from ..base import FieldNormalizer

class IntNormalizer(FieldNormalizer):
    def normalize(self, value):
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
