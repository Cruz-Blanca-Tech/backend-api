"""Corrector automático de apellidos de Padre/Madre corroborado por doble lectura.

Cubre la regla de negocio acordada: si el apellido del niño sale IDÉNTICO en la
FINS y en su DNI (DNIBE) — dos lecturas independientes, ~99% de confianza — y un
adulto (Padre/Madre) trae ese apellido con un error típico de OCR (TAFOR/TAFUR),
el sistema lo corrige en el dossier y deja una nota informativa. Sin la doble
lectura no se toca nada y la regla de coherencia sigue advirtiendo.
"""
import pytest

from src.contexts.data_quality_triage.application.shared.services.surname_auto_corrector import SurnameAutoCorrector
from src.contexts.data_quality_triage.domain.educa.rules.domain.family_rules import ParentLastNameCoherenceRule
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData
from src.contexts.data_quality_triage.domain.educa.value_objects.permissions_data import PermissionsData
from src.contexts.data_quality_triage.domain.educa.value_objects.religion_data import ReligionData
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult


def _dossier(ben_first: str = "YARELI ALEXANDRA", ben_last: str = "TAFUR MEDRANO", *adults) -> EducaInscriptionDossier:
    return EducaInscriptionDossier(
        beneficiary=BeneficiaryData(first_name=ben_first, last_name=ben_last),
        related_adults=FamilyData(adults=list(adults)),
        education=EducationData(),
        medical=MedicalData(),
        religion=ReligionData(),
        permissions=PermissionsData(),
    )


def _corrector(dossier, fins_last="TAFUR MEDRANO", dni_last="TAFUR MEDRANO") -> SurnameAutoCorrector:
    return SurnameAutoCorrector(
        dossier=dossier,
        fins_last_name=fins_last,
        child_dni_last_name=dni_last,
    )


def _coherence_warnings(dossier):
    return ParentLastNameCoherenceRule().evaluate(dossier)


# --- Con doble lectura corroborada: corrige ---------------------------------

def test_caso_real_tafor_tafur_corregido_y_sin_warning():
    """FINS y DNI del niño dicen TAFUR → el TAFOR del padre se unifica a TAFUR."""
    dossier = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFOR OBREGON"),
        RelatedAdult(relationship="MOTHER", full_name="MARIA MEDRANO QUISPE"),
    )

    notes = _corrector(dossier).correct()

    father = dossier.related_adults.adults[0]
    assert father.full_name == "JEFFER TIMOTEO TAFUR OBREGON"
    mother = dossier.related_adults.adults[1]
    assert mother.full_name == "MARIA MEDRANO QUISPE"  # ya correcto: intacta

    assert len(notes) == 1
    note = notes[0]
    assert note.severity == "INFO"
    assert note.field_name == "related_adults.adults[0].full_name"
    assert note.actual_value == "JEFFER TIMOTEO TAFOR OBREGON"
    assert "TAFOR" in note.rule_description and "TAFUR" in note.rule_description

    # La regla de coherencia ya no advierte sobre este caso.
    assert _coherence_warnings(dossier) == []


def test_ordena_invertido_en_el_dni_tambien_corroborado():
    """Aunque el DNI liste los apellidos en otro orden, la coincidencia vale."""
    dossier = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFOR OBREGON"),
    )
    notes = _corrector(dossier, dni_last="MEDRANO TAFUR").correct()
    assert dossier.related_adults.adults[0].full_name == "JEFFER TIMOTEO TAFUR OBREGON"
    assert len(notes) == 1


def test_mas_de_un_apellido_mal_leido_corrige_solo_los_corroborados():
    """La madre trae una variante de TAFUR y el padre también; ambos se unifican."""
    dossier = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="LUIS TAFOR OBREGON"),
        RelatedAdult(relationship="MOTHER", full_name="MARIA TAFURO GARCIA"),
    )
    notes = _corrector(dossier).correct()
    names = [a.full_name for a in dossier.related_adults.adults]
    assert "LUIS TAFUR OBREGON" in names
    assert "MARIA TAFUR GARCIA" in names
    assert len(notes) == 2


def test_adulto_other_no_se_corrige():
    dossier = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="LUIS TAFOR OBREGON"),
        RelatedAdult(relationship="OTHER", full_name="PEDRO TAFOR SANCHEZ"),
    )
    notes = _corrector(dossier).correct()
    assert dossier.related_adults.adults[0].full_name == "LUIS TAFUR OBREGON"
    assert dossier.related_adults.adults[1].full_name == "PEDRO TAFOR SANCHEZ"
    assert len(notes) == 1


def test_apellido_distinto_de_verdad_no_se_corrige_y_advierte():
    """El padre no comparte apellido ni con ruido de OCR → sigue la advertencia."""
    dossier = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN PEREZ OBREGON"),
    )
    notes = _corrector(dossier).correct()
    assert notes == []
    assert dossier.related_adults.adults[0].full_name == "JUAN PEREZ OBREGON"
    assert len(_coherence_warnings(dossier)) == 1


# --- Sin doble lectura: no corrige (y la regla advierte) ---------------------

def test_sin_dni_del_nino_no_corrige():
    """Falta el DNI del niño (DNIBE): no hay corroboración → nada que corregir."""
    dossier = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFOR OBREGON"),
    )
    notes = _corrector(dossier, dni_last=None).correct()
    assert notes == []
    assert dossier.related_adults.adults[0].full_name == "JEFFER TIMOTEO TAFOR OBREGON"
    assert len(_coherence_warnings(dossier)) == 1


def test_sin_fins_no_corrige():
    dossier = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFOR OBREGON"),
    )
    notes = _corrector(dossier, fins_last=None).correct()
    assert notes == []
    assert len(_coherence_warnings(dossier)) == 1


def test_doble_lectura_desacuerda_no_corrige():
    """El DNI del niño lee otro apellido (FLORES) → sin coincidencia → no corrige."""
    dossier = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFOR OBREGON"),
    )
    notes = _corrector(dossier, dni_last="FLORES GUTIERREZ").correct()
    assert notes == []
    assert dossier.related_adults.adults[0].full_name == "JEFFER TIMOTEO TAFOR OBREGON"
    assert len(_coherence_warnings(dossier)) == 1


def test_duplica_coincidencia_fins_sola_no_basta():
    """TAFUR solo en la FINS (aunque el adulto no la comparte) no dispara la
    corrección si el DNI del niño no trae esa lectura."""
    dossier = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="MOTHER", full_name="MARIA MEDRANO QUISPE"),
    )
    # El DNI del niño trae solo el apellido materno.
    notes = _corrector(dossier, dni_last="MEDRANO TAFUR").correct()
    # TAFUR sí está corroborado pero la madre ya lo escribe igual; MEDRANO está
    # exacto. Nada que corregir.
    assert notes == []
    assert dossier.related_adults.adults[0].full_name == "MARIA MEDRANO QUISPE"


def test_correccion_idempotente():
    """Re-procesar un dossier ya corregido no vuelve a corregir ni a notar."""
    dossier = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFUR OBREGON"),
    )
    notes = _corrector(dossier).correct()
    assert notes == []
    assert dossier.related_adults.adults[0].full_name == "JEFFER TIMOTEO TAFUR OBREGON"