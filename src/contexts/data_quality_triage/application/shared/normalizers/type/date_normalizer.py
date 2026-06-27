from datetime import datetime
from ..base import FieldNormalizer

class DateNormalizer(FieldNormalizer):
    def normalize(self, value):
        if not value:
            return ""
        val_str = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                dt = datetime.strptime(val_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return val_str
