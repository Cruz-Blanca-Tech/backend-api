"""Regla de coherencia de apellidos Padre/Madre vs Beneficiario.

La regla SOLO advierte: no tolera diferencias de una sola letra por su cuenta.
La tolerancia de errores típicos de OCR (TAFOR/TAFUR) la aplica el
`SurnameAutoCorrector` únicamente cuando el apellido del niño está corroborado
por dos lecturas independientes (FINS + DNI). Sin esa corroboración, acá llega
una advertencia para revisión manual.
"""
import pytest

from src.contexts.data_quality_triage.domain.educa.rules.domain.family_rules import ParentLastNameCoherenceRule
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData
from src.contexts.data_quality_triage.domain.educa.value_objects.permissions_data import PermissionsData
from src.contexts.data_quality_triage.domain.educa.value_objects.religion_data import ReligionData
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult


def _dossier(ben_first: str, ben_last: str, *adults) -> EducaInscriptionDossier:
    return EducaInscriptionDossier(
        beneficiary=BeneficiaryData(first_name=ben_first, last_name=ben_last),
        related_adults=FamilyData(adults=list(adults)),
        education=EducationData(),
        medical=MedicalData(),
        religion=ReligionData(),
        permissions=PermissionsData(),
    )


def _warnings(entity: EducaInscriptionDossier):
    return ParentLastNameCoherenceRule().evaluate(entity)


# --- Apellidos que coinciden: NO debe advertir ------------------------------

def test_apellidos_exactos_no_genera_warning():
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFUR OBREGON"),
        RelatedAdult(relationship="MOTHER", full_name="MARIA MEDRANO QUISPE"),
    )
    assert _warnings(entity) == []


def test_un_solo_apellido_coincide_no_genera_warning():
    """El padre comparte el primer apellido; el materno no aplica sobre él."""
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFUR OBREGON"),
    )
    assert _warnings(entity) == []


def test_madre_y_padre_sin_relacion_no_genera_warning():
    """Ningún adulto con rol Padre/Madre → no se evalúa nada."""
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="OTHER", full_name="JUAN TAFOR OBREGON"),
    )
    assert _warnings(entity) == []


# --- Apellidos realmente distintos o SIN corroboración: advierte -------------

def test_apellidos_distintos_genera_warning():
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO CRUZ FLORES"),
    )
    issues = _warnings(entity)
    assert len(issues) == 1
    assert issues[0].severity == "WARNING"


def test_diferencia_de_una_vocal_sin_corroboracion_genera_warning():
    """TAFOR/TAFUR sin corroboración cruzada (solo la FINS): no puede afirmarse
    que sea ruido de OCR → sigue la advertencia."""
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFOR OBREGON"),
    )
    issues = _warnings(entity)
    assert len(issues) == 1
    assert issues[0].severity == "WARNING"


def test_s_z_sin_corroboracion_genera_warning():
    entity = _dossier(
        "YARELI ALEXANDRA", "PEREZ MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN PERES OBREGON"),
    )
    assert len(_warnings(entity)) == 1


def test_letra_de_mas_parecida_no_genera_warning():
    """QUISPES/QUISPE: parecido fuzzy alto (ratio > 0.80) → no advierte.
    Es el comportamiento histórico de la regla, no una tolerancia nueva."""
    entity = _dossier(
        "YARELI ALEXANDRA", "QUISPE MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN QUISPES PEREZ"),
    )
    assert _warnings(entity) == []


def test_consonante_de_arranque_distinta_parecida_no_genera_warning():
    """TORRES/CORRES: comparten 5 de 6 letras (ratio 0.83) → no advierte.
    Es el comportamiento histórico de la regla anterior."""
    entity = _dossier(
        "YARELI ALEXANDRA", "TORRES MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN CORRES PEREZ"),
    )
    assert _warnings(entity) == []


def test_consonante_de_arranque_distinta_muy_diferente_genera_warning():
    """SOSA/ROSA: difieren en la consonante inicial y el parecido queda bajo
    (ratio 0.75) → advierte (no es ruido de OCR)."""
    entity = _dossier(
        "YARELI ALEXANDRA", "SOSA MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN ROSA PEREZ"),
    )
    assert len(_warnings(entity)) == 1


def test_sustitucion_fuera_de_grupo_genera_warning():
    """POMA vs PONA: m/n no es una confusión típica del OCR."""
    entity = _dossier(
        "YARELI ALEXANDRA", "POMA MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN PONA PEREZ"),
    )
    assert len(_warnings(entity)) == 1


def test_dos_diferencias_generan_warning():
    """RAMOS vs RAMID: más de una letra distinta no es un error típico."""
    entity = _dossier(
        "YARELI ALEXANDRA", "RAMOS MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN RAMID PEREZ"),
    )
    assert len(_warnings(entity)) == 1