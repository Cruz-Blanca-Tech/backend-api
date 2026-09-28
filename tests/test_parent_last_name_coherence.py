"""Regla de coherencia de apellidos Padre/Madre vs Beneficiario.

Cubre el caso real que generaba falsos positivos: cuando el DNI y la FINS del
beneficiario escriben TAFUR y el OCR leyó TAFOR en el padre, es una lectura
(no otra familia) y la advertencia no debe saltar. También guarda que los
casos de apellidos realmente distintos sigan advirtiendo.
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


# --- Errores típicos de OCR que NO deben disparar la advertencia -----------

def test_tafur_tafor_es_error_de_ocr_no_genera_warning():
    """Caso real: el padre figura TAFOR y el beneficiario TAFUR (vocal o/u)."""
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFOR OBREGON"),
        RelatedAdult(relationship="MOTHER", full_name="MARIA MEDRANO QUISPE"),
    )
    assert _warnings(entity) == []


def test_sustitucion_vocal_sola_no_genera_warning():
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFOR OBREGON"),
    )
    assert _warnings(entity) == []


def test_s_z_no_genera_warning():
    entity = _dossier(
        "YARELI ALEXANDRA", "PEREZ MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN PERES OBREGON"),
    )
    assert _warnings(entity) == []


def test_letra_de_mas_no_genera_warning():
    entity = _dossier(
        "YARELI ALEXANDRA", "QUISPE MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN QUISPES PEREZ"),
    )
    assert _warnings(entity) == []


def test_apellidos_exactos_no_genera_warning():
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO TAFUR OBREGON"),
        RelatedAdult(relationship="MOTHER", full_name="MARIA MEDRANO QUISPE"),
    )
    assert _warnings(entity) == []


# --- Apellidos realmente distintos: la advertencia se mantiene -------------

def test_apellidos_distintos_genera_warning():
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JEFFER TIMOTEO CRUZ FLORES"),
    )
    issues = _warnings(entity)
    assert len(issues) == 1
    assert issues[0].severity == "WARNING"


def test_consonante_de_arranque_distinta_sigue_generando_warning():
    """TORRES vs CORRES: difieren en una consonante inicial; no es ruido de OCR."""
    entity = _dossier(
        "YARELI ALEXANDRA", "TORRES MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN CORRES PEREZ"),
    )
    issues = _warnings(entity)
    assert len(issues) == 1


def test_sustitucion_fuera_de_grupo_sigue_generando_warning():
    """POMA vs PONA: m/n no es una confusión típica del OCR."""
    entity = _dossier(
        "YARELI ALEXANDRA", "POMA MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN PONA PEREZ"),
    )
    issues = _warnings(entity)
    assert len(issues) == 1


def test_dos_diferencias_siguen_generando_warning():
    """RAMOS vs RAMID: más de una letra distinta no es un error típico."""
    entity = _dossier(
        "YARELI ALEXANDRA", "RAMOS MEDRANO",
        RelatedAdult(relationship="FATHER", full_name="JUAN RAMID PEREZ"),
    )
    issues = _warnings(entity)
    assert len(issues) == 1


def test_madre_y_padre_sin_relacion_no_genera_warning():
    """Ningún adulto con rol Padre/Madre → no se evalúa nada."""
    entity = _dossier(
        "YARELI ALEXANDRA", "TAFUR MEDRANO",
        RelatedAdult(relationship="OTHER", full_name="JUAN TAFOR OBREGON"),
    )
    assert _warnings(entity) == []