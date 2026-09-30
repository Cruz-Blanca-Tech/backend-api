"""N3: las reglas de dominio DJ/FINS no deben crashear con datos raros del OCR.

El crash histórico (caso 90928086) degradaba el dossier a fallback vacío. Estas
pruebas garantizan que validate_completeness NUNCA lance excepción ante datos
familiares malformados, y que las reglas DJ degraden a discrepancias.
"""
import pytest

from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData, RelatedAdult
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData
from src.contexts.data_quality_triage.domain.educa.value_objects.religion_data import ReligionData
from src.contexts.data_quality_triage.domain.educa.value_objects.permissions_data import PermissionsData
from src.contexts.data_quality_triage.domain.educa.rules.domain.family_rules import (
    DjFinsSignerCoherenceRule,
    DjSignerPresenceRule,
    ParentPresenceRule,
)


def _dossier(related_adults: FamilyData) -> EducaInscriptionDossier:
    return EducaInscriptionDossier(
        beneficiary=BeneficiaryData(),
        related_adults=related_adults,
        education=EducationData(),
        medical=MedicalData(),
        religion=ReligionData(),
        permissions=PermissionsData(),
    )


BAD_VALUES = [None, "", 12345678, 0.5, ["X"], {"v": "x"}, "  "]


@pytest.mark.parametrize("weird", BAD_VALUES)
def test_dj_fins_coherence_rule_nunca_crashea(weird):
    entity = _dossier(FamilyData(fins_guardian_dni=weird, dj_signer_dni=weird))
    issues = DjFinsSignerCoherenceRule().evaluate(entity)
    assert isinstance(issues, list)


@pytest.mark.parametrize("weird", BAD_VALUES)
def test_dj_signer_presence_rule_nunca_crashea(weird):
    entity = _dossier(FamilyData(dj_signer_dni=weird))
    issues = DjSignerPresenceRule().evaluate(entity)
    assert isinstance(issues, list)


def test_dj_fins_coherence_mismatch_genera_warning():
    entity = _dossier(FamilyData(fins_guardian_dni="12345678", dj_signer_dni="87654321"))
    issues = DjFinsSignerCoherenceRule().evaluate(entity)
    assert len(issues) == 1
    assert issues[0].severity == "WARNING"
    assert issues[0].field_name == "related_adults.dj_signer"


def test_dj_fins_coherence_iguales_no_genera_issue():
    entity = _dossier(FamilyData(fins_guardian_dni="12345678", dj_signer_dni="12345678"))
    assert DjFinsSignerCoherenceRule().evaluate(entity) == []


def test_dj_signer_presence_avisa_cuando_falta():
    entity = _dossier(FamilyData(dj_signer_dni=None))
    issues = DjSignerPresenceRule().evaluate(entity)
    assert len(issues) == 1
    assert issues[0].severity == "WARNING"
    assert issues[0].field_name == "related_adults.dj_signer"


@pytest.mark.parametrize("family_kwargs", [
    {"dj_signer_dni": None},
    {"fins_guardian_dni": None, "dj_signer_dni": None},
    {"dj_signer_dni": 12345678},
    {"fins_guardian_dni": {"v": "x"}, "dj_signer_dni": ["A"]},
    {"guardian_dni": None, "dj_signer_dni": "   "},
])
def test_validate_completeness_nunca_lanza_con_familia_malformada(family_kwargs):
    entity = _dossier(FamilyData(**family_kwargs))
    # No debe lanzar excepción (antes degradaba el dossier a fallback vacío).
    is_valid, issues = entity.validate_completeness()
    assert isinstance(is_valid, bool)
    assert isinstance(issues, list)


def test_parent_presence_rule_no_advierte_si_hay_madre_o_padre():
    only_mother = _dossier(
        FamilyData(adults=[RelatedAdult(relationship="MOTHER", dni="48100010", full_name="MILAGROS QUISPE")])
    )
    only_father = _dossier(
        FamilyData(adults=[RelatedAdult(relationship="FATHER", dni="10778773", full_name="CARLOS LOPEZ")])
    )
    assert ParentPresenceRule().evaluate(only_mother) == []
    assert ParentPresenceRule().evaluate(only_father) == []


def test_parent_presence_rule_advierte_solo_si_no_hay_padre_ni_madre():
    only_other = _dossier(
        FamilyData(adults=[RelatedAdult(relationship="OTHER", dni="99887766", full_name="TIA MARIA")])
    )
    issues = ParentPresenceRule().evaluate(only_other)
    assert len(issues) == 1
    assert issues[0].severity == "WARNING"
    assert "ni al Padre ni a la Madre" in issues[0].rule_description