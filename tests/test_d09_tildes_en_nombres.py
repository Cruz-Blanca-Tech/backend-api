"""D9 (HU-004): el normalizador de nombres no debe quitar tildes ni la ñ.
Mayúsculas y espacios sí se pueden normalizar.

Se prueba (1) `NameNormalizer` directamente y (2) el camino real del OCR
(arnés de CP-05): nombres de la FINS → `case.dossier_data["beneficiary"]`.
Contraste: un nombre sin tildes con espacios de más se normaliza. Datos ficticios.
"""
import pytest
import unicodedata
from uuid import uuid4
from unittest.mock import patch

from src.contexts.data_quality_triage.application.shared.normalizers.type.name_normalizer import NameNormalizer
import tests.test_cp05_documentos_expediente_registro as cp05

CASOS = {"José": "JOSÉ", "María Ángeles": "MARÍA ÁNGELES", "Núñez Peña": "NÚÑEZ PEÑA"}
_nfc = lambda s: unicodedata.normalize("NFC", s or "")

pytestmark = pytest.mark.asyncio


class TestD9TildesEnNombres:
    @pytest.mark.parametrize("entrada", list(CASOS))
    def test_normalizador_conserva_tildes_y_enie(self, entrada):
        obtenido = _nfc(NameNormalizer().normalize(entrada)).upper()
        assert obtenido == CASOS[entrada], f"HALLAZGO (D9): «{entrada}» queda como «{obtenido}» (pierde tildes o ñ)."

    def test_contraste_mayusculas_y_espacios_se_normalizan(self):
        assert NameNormalizer().normalize("  juan   carlos ") == "JUAN CARLOS"

    async def test_camino_ocr_conserva_tildes_en_el_expediente(self):
        base = cp05._fins()
        fins = {**base, "child_first_name": "José María", "child_last_name": "Núñez Peña"}
        with patch.object(cp05, "_fins", return_value=fins):
            case = await cp05._procesar_ocr(uuid4())
        b = case.dossier_data["beneficiary"]
        nombre = _nfc(f"{b.get('first_name')} {b.get('last_name')}").upper()
        assert "JOSÉ" in nombre and "NÚÑEZ" in nombre and "PEÑA" in nombre, (
            f"HALLAZGO (D9): en el expediente el nombre queda «{nombre}» (pierde tildes o ñ)."
        )
