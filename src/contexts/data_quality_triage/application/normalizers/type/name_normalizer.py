from ..base import FieldNormalizer
import unicodedata
import re

class NameNormalizer(FieldNormalizer):
    def normalize(self, value):
        if not value:
            return ""
        val_str = str(value).strip()
        if not val_str:
            return ""
        val_str = "".join(
            c for c in unicodedata.normalize('NFD', val_str)
            if unicodedata.category(c) != 'Mn'
        )
        val_str = val_str.upper()
        val_str = re.sub(r'[^A-Z0-9\s]', ' ', val_str)
        return " ".join(val_str.split())
