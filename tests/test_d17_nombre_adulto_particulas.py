"""D17: el nombre completo del adulto se reparte en nombres y apellidos sin romper las particulas."""
import pytest

from src.contexts.core_beneficiary_management.application.mappers.educa_dossier_mapper import split_adult_full_name


@pytest.mark.parametrize("full_name,expected", [
    ("Juan Perez", ("Juan", "Perez")),
    ("Juan Perez Lopez", ("Juan", "Perez Lopez")),
    ("Juan Carlos Perez Lopez", ("Juan Carlos", "Perez Lopez")),
    ("Maria de la Cruz Perez", ("Maria", "de la Cruz Perez")),
    ("Ana Perez de la Torre", ("Ana", "Perez de la Torre")),
    ("Rosa Gomez del Castillo", ("Rosa", "Gomez del Castillo")),
    ("Luis", ("Luis", "")),
    ("De la De", ("De la De", "")),
    ("   ", ("", "")),
    (None, ("", "")),
])
def test_split_adult_full_name(full_name, expected):
    assert split_adult_full_name(full_name) == expected
