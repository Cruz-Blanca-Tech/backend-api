"""Tests del buscador fuzzy de beneficiarios contra el maestro (persons)."""
import asyncio

from src.contexts.data_quality_triage.application.shared.services.beneficiary_fuzzy_matcher import (
    BeneficiaryFuzzyMatcher,
    normalize_name,
    score_candidate,
)


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return list(self._rows)


class _FakeSession:
    """Sesión falsa: devuelve las filas que se le inyectan, sin tocar la BD."""

    def __init__(self, rows):
        self._rows = rows

    async def execute(self, statement, params=None):
        return _FakeResult(self._rows)


def _run(rows, **kwargs):
    matcher = BeneficiaryFuzzyMatcher(_FakeSession(rows))
    return asyncio.run(
        matcher.find_suggestions(
            first_name=kwargs.get("first_name", "MATEO CI"),
            last_name=kwargs.get("last_name", "DELGADO NAVARRO"),
            dni=kwargs.get("dni", "81000054"),
            limit=kwargs.get("limit", 3),
        )
    )


# --- Helpers puros ----------------------------------------------------------


def test_normalize_name_strips_accents_punctuation_and_case():
    assert normalize_name("JOSÉ MARÍA DELGADO-GÓMEZ") == "jose maria delgado gomez"
    assert normalize_name("  MATEO  CI  ") == "mateo ci"
    assert normalize_name(None) == ""


def test_score_candidate_weights():
    # Nombre idéntico + DNI cercano → casi 1.
    s = score_candidate("MATEO", "DELGADO", "81000054", "MATEO", "DELGADO", "81000034")
    assert s > 0.85
    # Nada en común (ni apellido ni DNI) → cerca de 0.
    s = score_candidate("MARIA", "QUISPE", "11111111", "PEDRO", "GUTIERREZ", "99999999")
    assert s < 0.3
    # Apellidos compartidos pero nombre de pila distinto → puntaje medio.
    s = score_candidate("JHON", "DELGADO NAVARRO", "22113344", "PEDRO", "DELGADO NAVARRO", "99887766")
    assert 0.5 <= s < 0.8


# --- Caso de negocio (ANDRE) -----------------------------------------------


def test_mateo_case_suggests_master_with_different_dni():
    # OCR leyó mal el DNI: el maestro tiene el nombre idéntico con otro DNI
    # (81000054 -> 81000034). Debe sugerirse, no ocultarse.
    suggestions = _run([("MATEO CI", "DELGADO NAVARRO", "81000034")])
    assert len(suggestions) == 1
    assert suggestions[0].dni == "81000034"
    assert suggestions[0].score > 0.7


def test_identical_dni_is_excluded_as_match_mdm():
    # Mismo DNI y mismo nombre → match MDM de identidad, nunca sugerencia.
    suggestions = _run([("MATEO CI", "DELGADO NAVARRO", "81000054")])
    assert suggestions == []


def test_homonym_same_name_different_dni_is_suggested():
    suggestions = _run(
        [("PEDRO GUTIERREZ", "FLORES", "87654321")],
        first_name="PEDRO GUTIERREZ", last_name="FLORES", dni="12345678",
    )
    assert len(suggestions) == 1
    assert suggestions[0].dni == "87654321"


# --- Robustez del match ----------------------------------------------------


def test_accents_are_normalized():
    suggestions = _run(
        [("JOSÉ", "DELGADO GÓMEZ", "70123456")],
        first_name="JOSE", last_name="DELGADO GOMEZ", dni="90000101",
    )
    assert len(suggestions) == 1
    assert suggestions[0].dni == "70123456"


def test_ocr_typo_in_given_name_still_matches_by_surname():
    suggestions = _run(
        [("PEDRO", "DELGADO NAVARRO", "99887766")],
        first_name="JHON", last_name="DELGADO NAVARRO", dni="99887755",
    )
    assert len(suggestions) == 1
    assert suggestions[0].dni == "99887766"


def test_swapped_first_and_last_columns_still_match():
    # El maestro guardó el nombre apellido-primero.
    suggestions = _run([("DELGADO NAVARRO", "MATEO CI", "81000034")])
    assert len(suggestions) == 1
    assert suggestions[0].dni == "81000034"


def test_second_given_name_intermediate_does_not_break_match():
    # El OCR añadió un segundo nombre de pila que el maestro no tiene.
    suggestions = _run(
        [("MATEO", "DELGADO NAVARRO", "81000034")],
        first_name="MATEO MIGUEL CI", last_name="DELGADO NAVARRO", dni="81000054",
    )
    assert len(suggestions) == 1
    assert suggestions[0].dni == "81000034"


# --- Falsos positivos ------------------------------------------------------


def test_no_match_returns_empty():
    suggestions = _run(
        [("PEDRO GUTIERREZ", "FLORES", "87654321")],
        first_name="MARIA", last_name="QUISPE HUAMAN", dni="12345678",
    )
    assert suggestions == []


def test_dni_proximity_alone_does_not_trigger():
    # El DNI parecido SIN coincidencia de nombre no debe sugerir (evita ruido).
    suggestions = _run(
        [("CARLOS LOPEZ", "GARCIA", "88887766")],
        first_name="JUAN", last_name="PEREZ RAMOS", dni="88886677",
    )
    assert suggestions == []


# --- Ranking, dedupe y límite ----------------------------------------------


def test_ranking_prefers_best_match():
    suggestions = _run([
        ("PEDRO", "DELGADO NAVARRO", "99999999"),   # solo apellido
        ("ANA", "CIFUENTES", "90000102"),          # apellido parecido, nombre otro
        ("MATEO CI", "DELGADO NAVARRO", "81000034"),  # el mejor: nombre idéntico
    ])
    assert len(suggestions) >= 1
    assert suggestions[0].dni == "81000034"


def test_same_dni_rows_are_deduplicated_keeping_best():
    suggestions = _run([
        ("MATEO A", "DELGADO NAVARRO", "81000034"),
        ("MATEO CI", "DELGADO NAVARRO", "81000034"),
    ])
    assert len(suggestions) == 1
    assert suggestions[0].first_name == "MATEO CI"


def test_limit_caps_suggestions():
    rows = [
        ("MATEO CI", "DELGADO NAVARRO", "81000034"),
        ("MATEO S", "DELGADO NAVARRO", "91234567"),
        ("MATEO R", "DELGADO NAVARRO", "92234567"),
        ("MATEO J", "DELGADO NAVARRO", "93234567"),
    ]
    suggestions = _run(rows, limit=2)
    assert len(suggestions) == 2