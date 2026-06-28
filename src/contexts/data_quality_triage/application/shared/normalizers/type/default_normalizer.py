from ..base import FieldNormalizer

class DefaultNormalizer(FieldNormalizer):
    def normalize(self, value):
        return value
