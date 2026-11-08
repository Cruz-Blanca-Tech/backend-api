from ..base import FieldNormalizer
import unicodedata
import re

_SPANISH_LETTERS = "ÁÉÍÓÚÜÑ"

class NameNormalizer(FieldNormalizer):
    def normalize(self, value):
        if not value:
            return ""
        val_str = str(value).strip()
        if not val_str:
            return ""
        # D9: el valor que se guarda conserva las letras del español (tildes, Ü, Ñ).
        # Cualquier otro diacrítico se reduce a su letra base. Para COMPARAR nombres
        # se usa name_match_key() (sin tildes), no este valor.
        val_str = unicodedata.normalize('NFC', val_str).upper()
        val_str = "".join(
            c if c in _SPANISH_LETTERS else "".join(
                d for d in unicodedata.normalize('NFD', c)
                if unicodedata.category(d) != 'Mn'
            )
            for c in val_str
        )
        val_str = re.sub(r'[0-9]+', ' ', val_str)
        val_str = re.sub(r'[^A-ZÁÉÍÓÚÜÑ\s]', ' ', val_str)
        return " ".join(val_str.split())
