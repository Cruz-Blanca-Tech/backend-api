"""D8 (HU-004 / HU-005): un DNI mal leído («1234567-8», o dígitos sueltos de
fragmentos distintos) no debe convertirse en un DNI de 8 dígitos; debe quedar
sin valor para que el expediente vaya a revisión.

Caminos reales que se ejercitan (sin red)
-----------------------------------------
1. FINS: `FinsRaw` → `FinsEnrichedMapper` con el `NormalizerRegistry` real
   (`DniNormalizer`) → `child_dni.normalized_value`.
2. Copia del DNI (DNIBE/DNIAP): `DniRaw.from_dict` (limpieza del payload de
   Azure) → `DniEnrichedMapper` → `document_number.normalized_value`.

Entradas mal leídas (todas ficticias):
  - "1234567-8"        7 dígitos + dígito verificador
  - "1234567 - 8"      ídem con espacios
  - "123 ABC 45678"    dos fragmentos separados por texto
  - "Nro 1234567 Tel 8" dígitos de campos distintos
Contraste: "12345678" se acepta tal cual.

Si la versión arma un DNI de 8 dígitos con esas entradas, el test FALLA con un
mensaje que empieza con «HALLAZGO».
"""
import re
import pytest

from src.contexts.data_quality_triage.application.educa.dtos.raw.fins_raw import FinsRaw
from src.contexts.data_quality_triage.application.educa.dtos.raw.dni_raw import DniRaw
from src.contexts.data_quality_triage.application.educa.mappers.enriched.fins_enriched_mapper import (
    FinsEnrichedMapper,
)
from src.contexts.data_quality_triage.application.educa.mappers.enriched.dni_enriched_mapper import (
    DniEnrichedMapper,
)
from src.contexts.data_quality_triage.application.shared.services.normalize_registry import NormalizerRegistry

MAL_LEIDOS = ["1234567-8", "1234567 - 8", "123 ABC 45678", "Nro 1234567 Tel 8"]


def _dni_fins(valor):
    enriched = FinsEnrichedMapper(NormalizerRegistry()).map(FinsRaw.from_dict({"child_dni": valor}))
    return enriched.child_dni.normalized_value if enriched.child_dni else None


def _dni_copia(valor):
    enriched = DniEnrichedMapper(NormalizerRegistry()).map(DniRaw.from_dict({"DocumentNumber": valor}))
    return enriched.document_number.normalized_value if enriched.document_number else None


def _es_dni_armado(v):
    return v is not None and re.fullmatch(r"\d{8}", str(v)) is not None


class TestD8DniFragmentado:

    @pytest.mark.parametrize("valor", MAL_LEIDOS)
    def test_fins_no_arma_un_dni(self, valor):
        obtenido = _dni_fins(valor)
        assert not _es_dni_armado(obtenido), (
            f"HALLAZGO (D8) [FINS]: la lectura mal hecha {valor!r} se convirtió en el DNI {obtenido!r}; "
            "DniNormalizer junta los dígitos en vez de rechazar el valor."
        )

    @pytest.mark.parametrize("valor", MAL_LEIDOS)
    def test_copia_dni_no_arma_un_dni(self, valor):
        obtenido = _dni_copia(valor)
        assert not _es_dni_armado(obtenido), (
            f"HALLAZGO (D8) [copia del DNI]: la lectura mal hecha {valor!r} se convirtió en el DNI {obtenido!r}; "
            "la limpieza de DniRaw (quita guiones y espacios) y DniNormalizer (junta dígitos) arman el número."
        )

    def test_contraste_dni_valido_se_acepta(self):
        assert _dni_fins("12345678") == "12345678"
        assert _dni_copia("12345678") == "12345678"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
