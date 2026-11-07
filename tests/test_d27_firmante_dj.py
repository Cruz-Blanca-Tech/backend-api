"""D27: el firmante de la DJ es valido si es padre, madre o apoderado registrados."""
from types import SimpleNamespace

from src.contexts.data_quality_triage.domain.educa.rules.domain.family_rules import DjFinsSignerCoherenceRule


def _dossier(signer, guardian, adults):
    related = SimpleNamespace(
        fins_guardian_dni=guardian, dj_signer_dni=signer,
        adults=[SimpleNamespace(relationship=r, dni=d) for r, d in adults],
    )
    return SimpleNamespace(related_adults=related)


ADULTS = [("FATHER", "10000001"), ("MOTHER", "10000002")]


def test_firma_el_padre_y_la_apoderada_es_la_madre_no_advierte():
    assert DjFinsSignerCoherenceRule().evaluate(_dossier("10000001", "10000002", ADULTS)) == []


def test_firma_la_apoderada_no_advierte():
    assert DjFinsSignerCoherenceRule().evaluate(_dossier("10000002", "10000002", ADULTS)) == []


def test_firmante_desconocido_si_advierte():
    issues = DjFinsSignerCoherenceRule().evaluate(_dossier("99999999", "10000002", ADULTS))
    assert len(issues) == 1 and issues[0].severity == "WARNING"
