# application/normalizers/bool_normalizer.py

import re

from src.contexts.data_quality_triage.application.shared.normalizers.base import FieldNormalizer



class BoolNormalizer(FieldNormalizer):

    TRUE_VALUES = {"true", "1", "yes", "y", "si", "sí", "t", "selected", "sì", "x", "51", "s1", "sl"}
    FALSE_VALUES = {"false", "0", "no", "n", "f", "unselected", "none", "null"}

    def normalize(self, value):

        if value is None:
            return None

        if isinstance(value, bool):
            return value

        value = re.sub(r"[.,;:!]+$", "", str(value).strip().lower()).strip()

        if value in self.TRUE_VALUES:
            return True        

        if value in self.FALSE_VALUES:
            return False

        return None