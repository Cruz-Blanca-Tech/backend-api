"""D9: al conservar tildes y ñ en el valor guardado, las COMPARACIONES de nombres
deben seguir siendo insensibles a tildes («NÚÑEZ» = «NUNEZ», «PEÑA» = «PENA»).

Cubre los 4 sitios que antes dependían de que el normalizador entregara ASCII:
1. Autocorrector de apellidos (no lo trata como error de OCR).
2. Coherencia de apellidos Padre/Madre (sin ERROR).
3. Fusión de adultos FINS/DJ en FamilyDomainMapper (misma persona) y la
   inferencia de rol por apellido del niño.
4. Deduplicación de adultos en FamilySchema (sin duplicado falso).
Datos ficticios.
"""
from types import SimpleNamespace

import pytest

from src.contexts.data_quality_triage.application.educa.schemas.family_schemas import FamilySchema
from src.contexts.data_quality_triage.application.shared.services.surname_auto_corrector import SurnameAutoCorrector
from src.contexts.data_quality_triage.domain.educa.mappers.family_domain_mapper import FamilyDomainMapper
from src.contexts.data_quality_triage.domain.educa.rules.domain.family_rules import ParentLastNameCoherenceRule
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedAdult, EnrichedDj
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData
from src.contexts.data_quality_triage.domain.educa.value_objects.permissions_data import PermissionsData
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult
from src.contexts.data_quality_triage.domain.educa.value_objects.religion_data import ReligionData
from src.contexts.data_quality_triage.domain.shared.value_objects.enriched_field import EnrichedField

# (con tilde, sin tilde)
PARES = [("NÚÑEZ", "NUNEZ"), ("PEÑA", "PENA")]
IDS = ["NUNEZ", "PENA"]


def _dossier(ben_first, ben_last, *adults):
    return EducaInscriptionDossier(
        beneficiary=BeneficiaryData(first_name=ben_first, last_name=ben_last),
        related_adults=FamilyData(adults=list(adults)),
        education=EducationData(),
        medical=MedicalData(),
        religion=ReligionData(),
        permissions=PermissionsData(),
    )


def _f(value):
    return EnrichedField(name="x", raw_value=value, normalized_value=value)


def _fins(child_first, child_last, *adults):
    # Solo los atributos que FamilyDomainMapper lee de la FINS.
    return SimpleNamespace(
        child_dni=_f(None),
        child_first_name=_f(child_first),
        child_last_name=_f(child_last),
        adults=list(adults),
        emergency_contact_phone=_f(None),
    )


def _adult(role, first, last):
    return EnrichedAdult(role=role, dni=_f(None), first_name=_f(first), last_name=_f(last), phone=_f(None))


# --- 1. Autocorrector de apellidos ------------------------------------------

@pytest.mark.parametrize("con_tilde,sin_tilde", PARES, ids=IDS)
def test_autocorrector_no_trata_la_tilde_como_error_de_ocr(con_tilde, sin_tilde):
    """El niño trae el apellido con tilde (FINS y DNI); el padre, sin tilde."""
    child_last = f"{con_tilde} ROJAS"
    father_name = f"CARLOS {sin_tilde} SOTO"
    dossier = _dossier("JOSE", child_last, RelatedAdult(relationship="FATHER", full_name=father_name))

    notes = SurnameAutoCorrector(dossier=dossier, fins_last_name=child_last, child_dni_last_name=child_last).correct()

    assert notes == [], f"«{con_tilde}»/«{sin_tilde}» se trató como error de OCR: {[n.rule_description for n in notes]}"
    assert dossier.related_adults.adults[0].full_name == father_name


# --- 2. Coherencia de apellidos Padre/Madre ---------------------------------

@pytest.mark.parametrize("con_tilde,sin_tilde", PARES, ids=IDS)
@pytest.mark.parametrize("tilde_en", ["beneficiario", "adulto"])
def test_coherencia_de_apellidos_sin_error_por_tilde(con_tilde, sin_tilde, tilde_en):
    ben_last = f"{con_tilde if tilde_en == 'beneficiario' else sin_tilde} ROJAS"
    adult_last = con_tilde if tilde_en == "adulto" else sin_tilde
    dossier = _dossier("JOSE", ben_last, RelatedAdult(relationship="FATHER", full_name=f"CARLOS {adult_last} SOTO"))

    issues = ParentLastNameCoherenceRule().evaluate(dossier)

    assert issues == [], f"ERROR de coherencia falso: {[i.actual_value for i in issues]}"


# --- 3. FamilyDomainMapper: fusión FINS/DJ e inferencia de rol --------------

@pytest.mark.parametrize("con_tilde,sin_tilde", PARES, ids=IDS)
def test_mapper_fusiona_padre_de_fins_y_dj_como_la_misma_persona(con_tilde, sin_tilde):
    fins = _fins("JOSE", "ROJAS LUNA", _adult("FATHER", "CARLOS", f"{con_tilde} {con_tilde}"))
    dj = EnrichedDj(
        child_dni=_f(None),
        guardian_dni=_f(None),
        parents_father_name=_f(f"CARLOS {sin_tilde} {sin_tilde}"),
    )

    family = FamilyDomainMapper().map(fins, dj)

    fathers = [a for a in family.adults if a.relationship == "FATHER"]
    assert len(fathers) == 1, f"el mismo padre quedó duplicado: {[a.full_name for a in fathers]}"


@pytest.mark.parametrize("con_tilde,sin_tilde", PARES, ids=IDS)
def test_mapper_infiere_padre_por_apellido_paterno_con_o_sin_tilde(con_tilde, sin_tilde):
    """Niño «X ROJAS» con tilde; adulto sin rol (OTHER) con el apellido paterno sin tilde."""
    fins = _fins("JOSE", f"{con_tilde} ROJAS", _adult("OTHER", "CARLOS", f"{sin_tilde} SOTO"))

    family = FamilyDomainMapper().map(fins, None)

    assert [a.relationship for a in family.adults] == ["FATHER"]


# --- 4. FamilySchema: deduplicación de adultos ------------------------------

@pytest.mark.parametrize("con_tilde,sin_tilde", PARES, ids=IDS)
def test_schema_mismo_dni_con_y_sin_tilde_no_es_duplicado(con_tilde, sin_tilde):
    family = FamilySchema(adults=[
        {"relationship": "FATHER", "dni": "10000001", "full_name": f"CARLOS {con_tilde} SOTO"},
        {"relationship": "TUTOR", "dni": "10000001", "full_name": f"CARLOS {sin_tilde} SOTO"},
    ])

    assert len(family.adults) == 1, f"duplicado falso: {[a.full_name for a in family.adults]}"
