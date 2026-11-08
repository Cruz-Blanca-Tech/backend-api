"""D22: el triaje no debe aprobar un beneficiario con nombre o apellido en blanco o de 1 letra."""
import pytest

from src.contexts.data_quality_triage.application.shared.factories.dossier_factory import DossierFactory
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType


def _issues(first_name, last_name):
    dossier = DossierFactory.reconstitute(
        {"beneficiary": {"dni": "12345678", "first_name": first_name, "last_name": last_name,
                         "birth_date": "2016-01-01", "gender": "F"}},
        ActivityType("EDUCA_INSCRIPTION"),
    )
    _, issues = dossier.validate_completeness()
    return [i for i in issues if i.field_name == "beneficiary.name" and i.severity == "ERROR"]


@pytest.mark.parametrize("first_name,last_name", [
    ("", ""), ("   ", "  "), ("Ana", ""), ("", "Perez"), ("Ana", "   "), ("A", "Perez"), ("Ana", "P"),
])
def test_nombre_invalido_genera_error(first_name, last_name):
    assert _issues(first_name, last_name)


def test_nombre_valido_no_genera_error():
    assert not _issues("Ana", "Perez")
    assert not _issues("  Ana Maria ", " Perez Lopez ")
