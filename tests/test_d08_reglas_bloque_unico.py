"""D8 (complemento de test_d08_dni_fragmentado.py): reglas acordadas para la
corrección «bloque único de 8 dígitos». Valores ficticios.

1. Si el texto trae más de un bloque de 8 dígitos («12345678 / 87654321»),
   no se elige uno: queda sin valor y el expediente va a revisión.
2. El dígito verificador tras el guion se descarta sin validarlo y se
   conservan los ceros a la izquierda («01234567-8» → «01234567»).

Se ejercitan los mismos caminos que en test_d08: FINS (FinsEnrichedMapper) y
copia del DNI (DniRaw → DniEnrichedMapper), sin red.
"""
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


def _dni_fins(valor):
    enriched = FinsEnrichedMapper(NormalizerRegistry()).map(FinsRaw.from_dict({"child_dni": valor}))
    return enriched.child_dni.normalized_value if enriched.child_dni else None


def _dni_copia(valor):
    enriched = DniEnrichedMapper(NormalizerRegistry()).map(DniRaw.from_dict({"DocumentNumber": valor}))
    return enriched.document_number.normalized_value if enriched.document_number else None


CAMINOS = [pytest.param(_dni_fins, id="fins"), pytest.param(_dni_copia, id="copia_dni")]


@pytest.mark.parametrize("leer", CAMINOS)
def test_dos_bloques_de_8_digitos_va_a_revision(leer):
    assert leer("12345678 / 87654321") is None


@pytest.mark.parametrize("leer", CAMINOS)
def test_digito_verificador_se_descarta_y_conserva_ceros_a_la_izquierda(leer):
    assert leer("01234567-8") == "01234567"
