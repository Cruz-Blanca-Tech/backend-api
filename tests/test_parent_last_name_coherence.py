"""Regla de coherencia de apellidos Padre/Madre vs Beneficiario.

El apellido del Padre y/o de la Madre DEBE coincidir con al menos
uno de los apellidos del beneficiario. Si no hay coincidencia, es
un ERROR: el operador debe corregirlo (OCR mal leído, rol mal
asignado, familiar equivocado). NO es una advertencia.

La tolerancia de errores típicos de OCR (TAFOR/TAFUR) la aplica el
`SurnameAutoCorrector` únicamente cuando el apellido del niño está corroborado
por dos lecturas independientes (FINS + DNI). Sin esa corroboración, acá llega
un ERROR para revisión obligatoria.
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


def _issues(entity: EducaInscriptionDossier):
    return ParentLastNameCoherenceRule().evaluate(entity)


# --- Apellidos que coinciden: NO debe error ------------------------------

def test_apellidos_exactos_no_genera_error():
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFUR OBREGON"),
        RelatedAdult(relationship="MOTHER", full_name="MARIA MEDRANO QUISPE"),
    )
    assert _issues(entity) == []


def test_un_solo_apellido_coincide_no_genera_error():
    """El padre comparte el primer apellido; el materno no aplica sobre él."""
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFUR OBREGON"),
    )
    assert _issues(entity) == []


def test_madre_y_padre_sin_relacion_no_genera_error():
    """Ningún adulto con rol Padre/Madre → no se evalúa nada."""
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="OTHER", full_name="JUAN TAFOR OBREGON"),
    )
    assert _issues(entity) == []


# --- Apellidos realmente distintos o SIN corroboración: ERROR -------------

def test_apellidos_distintos_genera_error():
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO CRUZ FLORES"),
    )
    issues = _issues(entity)
    assert len(issues) == 1
    assert issues[0].severity == "ERROR"


def test_diferencia_de_una_vocal_sin_corroboracion_genera_error():
    """TAFOR/TAFUR sin corroboración cruzada (solo la FINS): no puede afirmarse
    que sea ruido de OCR → sigue el error."""
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFOR OBREGON"),
    )
    issues = _issues(entity)
    assert len(issues) == 1
    assert issues[0].severity == "ERROR"


def test_s_z_sin_corroboracion_genera_error():
    entity = _dossier(
        "YARELI ALEXANDRA", "PEREZ MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN PERES OBREGON"),
    )
    assert len(_issues(entity)) == 1


def test_letra_de_mas_parecida_no_genera_error():
    """QUISPES/QUISPE: parecido fuzzy alto (ratio > 0.80) → no error.
    Es el comportamiento histórico de la regla, no una tolerancia nueva."""
    entity = _dossier(
        "YARELI ALEXANDRA", "QUISPE MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN QUISPES PEREZ"),
    )
    assert _issues(entity) == []


def test_consonante_de_arranque_distinta_parecida_no_genera_error():
    """TORRES/CORRES: comparten 5 de 6 letras (ratio 0.83) → no error.
    Es el comportamiento histórico de la regla anterior."""
    entity = _dossier(
        "YARELI ALEXANDRA", "TORRES MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN CORRES PEREZ"),
    )
    assert _issues(entity) == []


def test_consonante_de_arranque_distinta_muy_diferente_genera_error():
    """SOSA/ROSA: difieren en la consonante inicial y el parecido queda bajo
    (ratio 0.75) → error (no es ruido de OCR)."""
    entity = _dossier(
        "YARELI ALEXANDRA", "SOSA MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN ROSA PEREZ"),
    )
    assert len(_issues(entity)) == 1


def test_sustitucion_fuera_de_grupo_genera_error():
    """POMA vs PONA: m/n no es una confusión típica del OCR."""
    entity = _dossier(
        "YARELI ALEXANDRA", "POMA MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN PONA PEREZ"),
    )
    assert len(_issues(entity)) == 1


def test_dos_diferencias_generan_error():
    """RAMOS vs RAMID: más de una letra distinta no es un error típico."""
    entity = _dossier(
        "YARELI ALEXANDRA", "RAMOS MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN RAMID PEREZ"),
    )
    assert len(_issues(entity)) == 1