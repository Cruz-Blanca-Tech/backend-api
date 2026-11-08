"""D20: si el DNI del familiar ya existe en el maestro, se avisa en vez de vincular en silencio."""
from types import SimpleNamespace

from src.contexts.data_quality_triage.application.shared.services.dossier_processor import _build_existing_adult_notice

MASTER = SimpleNamespace(dni="40000001", first_name="Rosa", last_name="Quispe Mamani", phone="999111222")


def test_aviso_es_warning_y_no_bloquea():
    n = _build_existing_adult_notice(0, "Rosa Quispe Mamani", MASTER)
    assert n.severity == "WARNING"
    assert "40000001" in n.rule_description
    assert "se conservara" not in n.rule_description


def test_nombre_parecido_no_advierte_cambio():
    assert "se conservara" not in _build_existing_adult_notice(1, "Rosa Quispe", MASTER).rule_description


def test_nombre_distinto_avisa_que_se_conserva_el_del_maestro():
    n = _build_existing_adult_notice(2, "Maria Lopez Garcia", MASTER)
    assert "se conservara el nombre del maestro" in n.rule_description
    assert n.field_name == "related_adults.adults[2].dni"
