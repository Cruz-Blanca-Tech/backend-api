import pytest
from src.contexts.data_quality_triage.domain.educa.services.name_separator import (
    normalize_name_token,
    get_person_surnames,
    get_primary_paternal_surname,
    is_noise_text,
    separate_child_name_and_surnames,
)

def test_normalize_name_token():
    assert normalize_name_token("José María Pérez-Gómez 123") == "JOSE MARIA PEREZ GOMEZ"
    assert normalize_name_token("") == ""
    assert normalize_name_token(None) == ""

def test_get_person_surnames():
    assert get_person_surnames(None) == []
    assert get_person_surnames("") == []
    assert get_person_surnames("CARLOS") == ["CARLOS"]
    assert get_person_surnames("JUAN PEREZ") == ["PEREZ"]
    assert get_person_surnames("JUAN CARLOS PEREZ") == ["CARLOS", "PEREZ"]
    assert get_person_surnames("JUAN CARLOS PEREZ GOMEZ") == ["PEREZ", "GOMEZ"]

def test_get_primary_paternal_surname():
    assert get_primary_paternal_surname(None) is None
    assert get_primary_paternal_surname("") is None
    assert get_primary_paternal_surname("CARLOS") == "CARLOS"
    assert get_primary_paternal_surname("JUAN PEREZ") == "PEREZ"
    assert get_primary_paternal_surname("JUAN CARLOS PEREZ") == "CARLOS"
    assert get_primary_paternal_surname("JUAN CARLOS PEREZ GOMEZ") == "PEREZ"

def test_is_noise_text():
    assert is_noise_text("") is True
    assert is_noise_text(None) is True
    assert is_noise_text("12") is True
    assert is_noise_text("bir.") is True
    assert is_noise_text("none") is True
    assert is_noise_text("null") is True
    assert is_noise_text("-") is True
    assert is_noise_text("PEREZ") is False

def test_separate_child_name_and_surnames_empty():
    assert separate_child_name_and_surnames("", "") == ("", "")
    assert separate_child_name_and_surnames(None, None) == ("", "")

def test_separate_child_name_and_surnames_no_parents():
    fn, ln = separate_child_name_and_surnames("JUAN CARLOS", "PEREZ GOMEZ")
    assert fn == "JUAN CARLOS"
    assert ln == "PEREZ GOMEZ"

def test_separate_child_name_and_surnames_single_token_attached_suffix():
    fn, ln = separate_child_name_and_surnames(
        "ADRIANOMONTENEG",
        "",
        father_full_name="JUAN MONTENEGRO DIAZ"
    )
    assert fn == "ADRIANO"
    assert "MONTENEGRO" in ln

def test_separate_child_name_and_surnames_extracts_from_first_name():
    fn, ln = separate_child_name_and_surnames(
        "MATEO PEREZ",
        "",
        father_full_name="CARLOS PEREZ LOPEZ",
        mother_full_name="MARIA GOMEZ RUIZ"
    )
    assert fn == "MATEO"
    assert "PEREZ" in ln

def test_separate_child_name_and_surnames_replaces_noise_in_last_name():
    fn, ln = separate_child_name_and_surnames(
        "LUCIA PEREZ GOMEZ",
        "Bir.",
        father_full_name="CARLOS PEREZ",
        mother_full_name="ANA GOMEZ"
    )
    assert fn == "LUCIA"
    assert "PEREZ" in ln
    assert "GOMEZ" in ln

def test_separate_child_name_and_surnames_preserves_clean_when_already_separated():
    fn, ln = separate_child_name_and_surnames(
        "MATEO",
        "PEREZ GOMEZ",
        father_full_name="CARLOS PEREZ",
        mother_full_name="ANA GOMEZ"
    )
    assert fn == "MATEO"
    assert ln == "PEREZ GOMEZ"

def test_separate_child_name_and_surnames_attached_compound():
    fn, ln = separate_child_name_and_surnames(
        "DIEGO VALDEZPAZ",
        "",
        father_full_name="JOSE VALDEZ",
        mother_full_name="ANA PAZ"
    )
    assert "DIEGO" in fn
    assert "VALDEZ" in ln or "PAZ" in ln

def test_separate_child_name_and_surnames_existing_mother_prepends_father():
    fn, ln = separate_child_name_and_surnames(
        "SOFIA PEREZ",
        "GOMEZ",
        father_full_name="CARLOS PEREZ DIAZ",
        mother_full_name="ANA GOMEZ FLORES"
    )
    assert fn == "SOFIA"
    assert "PEREZ" in ln
    assert "GOMEZ" in ln
