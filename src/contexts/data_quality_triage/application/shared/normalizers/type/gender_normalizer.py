from ..base import FieldNormalizer

class GenderNormalizer(FieldNormalizer):
    def normalize(self, value: str) -> str:
        if value is None:
            return None
        val_str = str(value).strip().upper()
        if val_str in ["M", "MASCULINO", "HOMBRE", "H", "MASC"]:
            return "M"
        if val_str in ["F", "FEMENINO", "MUJER", "FEM"]:
            return "F"
        return "UNKNOWN"
