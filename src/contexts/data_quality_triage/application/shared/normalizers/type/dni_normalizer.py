import re

from ..base import FieldNormalizer

class DniNormalizer(FieldNormalizer):
    def normalize(self, value):
        if not value:
            return None
        val_str = str(value).strip()
        if not val_str:
            return None

        # D8: solo se acepta un único bloque de exactamente 8 dígitos, con texto
        # alrededor (p. ej. «DNI: 12345678») y, opcionalmente, guion + dígito
        # verificador («12345678-9»), que se descarta sin validarlo. No se juntan
        # dígitos de bloques distintos: cualquier otro caso devuelve None y el
        # expediente va a revisión.
        runs = re.findall(r"\d+", val_str)
        blocks_of_8 = [r for r in runs if len(r) == 8]
        if len(blocks_of_8) != 1:
            return None
        dni = blocks_of_8[0]
        others = list(runs)
        others.remove(dni)
        if not others:
            return dni
        if len(others) == 1 and len(others[0]) == 1 and re.search(r"\d{8}\s*-\s*\d(?!\d)", val_str):
            return dni

        return None
