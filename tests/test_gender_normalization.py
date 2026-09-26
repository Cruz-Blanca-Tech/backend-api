"""Tests de normalización de género: `_normalize_gender` (al guardar corrección)
y `GenderCoherenceRule` (tolerancia de M/F/MALE/FEMALE en el dominio).

Cubre los puntos 1a/1b: el maestro serializa el enum (MALE/FEMALE) y el OCR/FINS
usa M/F; ambos deben ser válidos y el payload corregido debe guardarse en M/F.
"""
import copy

from src.contexts.data_quality_triage.application.shared.factories.dossier_factory import DossierFactory
from src.contexts.data_quality_triage.application.shared.use_cases.submit_correction_use_case import SubmitCorrectionUseCase
from src.contexts.data_quality_triage.domain.educa.rules.domain.beneficiary_rules import GenderCoherenceRule
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
from tests.test_dossier_triage import RAW_PAYLOAD


# --- _normalize_gender ------------------------------------------------------


def test_normalize_gender_maps_mdm_enum_to_f_m():
    out = SubmitCorrectionUseCase._normalize_gender({"beneficiary": {"gender": "MALE"}})
    assert out["beneficiary"]["gender"] == "M"

    out = SubmitCorrectionUseCase._normalize_gender({"beneficiary": {"gender": "FEMALE"}})
    assert out["beneficiary"]["gender"] == "F"


def test_normalize_gender_keeps_f_m_and_lowercase():
    # M/F ya son válidos para el maestro: se conservan sin reescribir.
    assert SubmitCorrectionUseCase._normalize_gender({"beneficiary": {"gender": "M"}})["beneficiary"]["gender"] == "M"
    assert SubmitCorrectionUseCase._normalize_gender({"beneficiary": {"gender": "F"}})["beneficiary"]["gender"] == "F"
    # El enum del maestro en minúsculas también se mapea.
    assert SubmitCorrectionUseCase._normalize_gender({"beneficiary": {"gender": "female"}})["beneficiary"]["gender"] == "F"
    assert SubmitCorrectionUseCase._normalize_gender({"beneficiary": {"gender": "male"}})["beneficiary"]["gender"] == "M"


def test_normalize_gender_does_not_touch_other_cases():
    # Sin género: se deja como está (el panel lo marcará pendiente).
    data = {"beneficiary": {"gender": ""}}
    assert SubmitCorrectionUseCase._normalize_gender(data) is data
    # Genero no reconocido: se conserva para que el panel lo señale.
    data = {"beneficiary": {"gender": "X"}}
    assert SubmitCorrectionUseCase._normalize_gender(data)["beneficiary"]["gender"] == "X"
    # Sin sección beneficiary o datos no dict: no modifica nada.
    assert SubmitCorrectionUseCase._normalize_gender({"foo": 1}) == {"foo": 1}
    assert SubmitCorrectionUseCase._normalize_gender(None) is None


# --- GenderCoherenceRule ----------------------------------------------------


def _dossier_with_gender(gender: str):
    payload = copy.deepcopy(RAW_PAYLOAD)
    payload["beneficiary"]["gender"] = gender
    return DossierFactory.reconstitute(payload, ActivityType.EDUCA_INSCRIPTION)


def test_gender_coherence_accepts_m_f_male_female_case_insensitive():
    for g in ("M", "F", "MALE", "FEMALE", "m", "f", "male", "female"):
        issues = GenderCoherenceRule().evaluate(_dossier_with_gender(g))
        assert issues == [], f"gender={g} no debería generar issues: {issues}"


def test_gender_coherence_flags_invalid_values():
    issues = GenderCoherenceRule().evaluate(_dossier_with_gender("X"))
    assert len(issues) == 1
    assert issues[0].field_name == "beneficiary.gender"
    assert issues[0].severity == "ERROR"


def test_gender_coherence_ignores_missing_gender():
    payload = copy.deepcopy(RAW_PAYLOAD)
    payload["beneficiary"]["gender"] = None
    dossier = DossierFactory.reconstitute(payload, ActivityType.EDUCA_INSCRIPTION)
    assert GenderCoherenceRule().evaluate(dossier) == []