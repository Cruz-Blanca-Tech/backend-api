"""Tests de `EducaDossierMapper` para los comportamientos de la ronda de triaje:

- `_sync_guardian_emergency_flags`: al corregir un expediente de un beneficiario
  YA registrado en el MDM, el apoderado y el contacto de emergencia SÍ se pueden
  cambiar (los flags operativos se sincronizan con guardian_dni /
  emergency_contact_dni), sin tocar identidad ni roles FATHER/MOTHER.
- `_append_new_tutors`: solo se añaden tutores nuevos (rol distinto de
  padre/madre) que no sean la misma persona de un familiar existente
  (mismo DNI o nombre muy similar).
- Alta: deduplicación por DNI + flags de apoderado/emergencia.
"""
import uuid

from src.contexts.core_beneficiary_management.application.dtos.educa_dossier_dto import (
    EducaDossierDTO, EducaBeneficiaryDTO, EducaRelatedAdultsDTO, EducaAdultDTO
)
from src.contexts.core_beneficiary_management.application.mappers.educa_dossier_mapper import EducaDossierMapper
from src.contexts.core_beneficiary_management.domain.entities.adult import Adult
from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
from src.contexts.core_beneficiary_management.domain.value_objects.relationship_role import RelationshipRole


def _make_beneficiary(adults):
    b = Beneficiary(id=uuid.uuid4(), dni=DNI("12345678"), first_name="Juan", last_name="Perez")
    b.relatives = adults
    return b


def _make_adult(dni, full_name, role=RelationshipRole.OTHER,
                guardian=False, emergency=False):
    parts = full_name.split(" ", 1)
    return Adult(
        id=uuid.uuid4(),
        dni=DNI(dni),
        first_name=parts[0],
        last_name=parts[1] if len(parts) > 1 else "",
        role=role,
        is_guardian=guardian,
        is_emergency_contact=emergency,
    )


def _dto(adults, guardian_dni=None, emergency_contact_dni=None):
    return EducaDossierDTO(
        beneficiary=EducaBeneficiaryDTO(
            dni="12345678", first_name="Juan", last_name="Perez", gender="M"
        ),
        related_adults=EducaRelatedAdultsDTO(
            adults=adults,
            guardian_dni=guardian_dni,
            emergency_contact_dni=emergency_contact_dni,
        ),
    )


def _relatives_by_dni(beneficiary):
    return {r.dni.value: r for r in beneficiary.relatives}


# --- _sync_guardian_emergency_flags ----------------------------------------

def test_sync_sets_guardian_and_emergency_flags_on_existing_adults():
    existing = _make_beneficiary([
        _make_adult("48100010", "MILAGROS QUISPE", role=RelationshipRole.MOTHER),
        _make_adult("10778773", "CARLOS LOPEZ", role=RelationshipRole.FATHER),
    ])
    dto = _dto(
        adults=[EducaAdultDTO(dni="48100010", full_name="MILAGROS QUISPE", relationship="MOTHER")],
        guardian_dni="48100010",
        emergency_contact_dni="48100010",
    )

    updated = EducaDossierMapper.map_to_entity(dto, existing)
    by_dni = _relatives_by_dni(updated)

    # El apoderado y el contacto de emergencia se pueden cambiar aunque el
    # beneficiario ya esté en el MDM.
    assert by_dni["48100010"].is_guardian is True
    assert by_dni["48100010"].is_emergency_contact is True
    # El otro padre no recibe flags.
    assert by_dni["10778773"].is_guardian is False
    assert by_dni["10778773"].is_emergency_contact is False
    # No se agregan ni eliminan: los familiares del maestro se preservan.
    assert len(updated.relatives) == 2


def test_sync_moves_guardian_flag_when_change():
    existing = _make_beneficiary([
        _make_adult("48100010", "MILAGROS QUISPE", role=RelationshipRole.MOTHER, guardian=True),
        _make_adult("10778773", "CARLOS LOPEZ", role=RelationshipRole.FATHER),
    ])
    dto = _dto(
        adults=[EducaAdultDTO(dni="48100010", full_name="MILAGROS QUISPE", relationship="MOTHER")],
        guardian_dni="10778773",   # cambio: ahora el padre es el apoderado
        emergency_contact_dni="48100010",
    )

    updated = EducaDossierMapper.map_to_entity(dto, existing)
    by_dni = _relatives_by_dni(updated)

    assert by_dni["10778773"].is_guardian is True
    assert by_dni["48100010"].is_guardian is False
    assert by_dni["48100010"].is_emergency_contact is True


def test_sync_clears_flags_when_not_designated():
    existing = _make_beneficiary([
        _make_adult("48100010", "MILAGROS QUISPE", role=RelationshipRole.MOTHER,
                    guardian=True, emergency=True),
    ])
    dto = _dto(
        adults=[EducaAdultDTO(dni="48100010", full_name="MILAGROS QUISPE", relationship="MOTHER")],
        guardian_dni=None,
        emergency_contact_dni=None,
    )

    updated = EducaDossierMapper.map_to_entity(dto, existing)
    mother = _relatives_by_dni(updated)["48100010"]

    assert mother.is_guardian is False
    assert mother.is_emergency_contact is False


# --- _append_new_tutors ----------------------------------------------------

def test_append_keeps_parents_and_adds_only_new_tutor():
    existing = _make_beneficiary([
        _make_adult("48100010", "MILAGROS QUISPE", role=RelationshipRole.MOTHER),
    ])
    dto = _dto(
        adults=[
            EducaAdultDTO(dni="48100010", full_name="MILAGROS QUISPE", relationship="MOTHER"),
            EducaAdultDTO(dni="10778773", full_name="CARLOS LOPEZ", relationship="FATHER"),   # padre nuevo → NO se agrega
            EducaAdultDTO(dni="99887766", full_name="TIA MARIA", relationship="APODERADO"),   # tutora nueva → SÍ se agrega
        ],
        guardian_dni="99887766",
    )

    updated = EducaDossierMapper.map_to_entity(dto, existing)
    by_dni = _relatives_by_dni(updated)

    assert sorted(by_dni.keys()) == ["48100010", "99887766"]
    assert by_dni["99887766"].is_guardian is True
    assert by_dni["48100010"].is_guardian is False


def test_append_skips_same_dni_different_name():
    existing = _make_beneficiary([
        _make_adult("48100010", "MILAGROS QUISPE", role=RelationshipRole.TUTOR),
    ])
    dto = _dto(
        adults=[EducaAdultDTO(dni="48100010", full_name="OTRA PERSONA", relationship="APODERADO")]
    )

    updated = EducaDossierMapper.map_to_entity(dto, existing)

    assert len(updated.relatives) == 1
    assert updated.relatives[0].dni.value == "48100010"


def test_append_skips_similar_name_when_dni_differs():
    existing = _make_beneficiary([
        _make_adult("48100010", "MILAGROS QUISPE", role=RelationshipRole.TUTOR),
    ])
    dto = _dto(
        adults=[EducaAdultDTO(dni="99999999", full_name="MILAGROS QUISPE", relationship="APODERADO")]
    )

    updated = EducaDossierMapper.map_to_entity(dto, existing)

    assert len(updated.relatives) == 1
    assert updated.relatives[0].dni.value == "48100010"


def test_append_ignores_invalid_dni():
    existing = _make_beneficiary([
        _make_adult("48100010", "MILAGROS QUISPE", role=RelationshipRole.TUTOR),
    ])
    dto = _dto(
        adults=[
            EducaAdultDTO(dni="", full_name="SIN DNI", relationship="APODERADO"),
            EducaAdultDTO(dni="123", full_name="DNI CORTO", relationship="APODERADO"),
        ]
    )

    updated = EducaDossierMapper.map_to_entity(dto, existing)

    assert len(updated.relatives) == 1


# --- ALTA ------------------------------------------------------------------

def test_alta_deduplicates_by_dni_and_builds_flags():
    dto = _dto(
        adults=[
            EducaAdultDTO(dni="87654321", full_name="Papa Perez", relationship="FATHER"),
            EducaAdultDTO(dni="87654321", full_name="Papa Perez Duplicate", relationship="OTHER"),
            EducaAdultDTO(dni="11223344", full_name="Mama Perez", relationship="MOTHER"),
        ],
        guardian_dni="11223344",
        emergency_contact_dni="87654321",
    )

    beneficiary = EducaDossierMapper.map_to_entity(dto)
    by_dni = _relatives_by_dni(beneficiary)

    assert sorted(by_dni.keys()) == ["11223344", "87654321"]
    assert by_dni["11223344"].is_guardian is True
    assert by_dni["87654321"].is_emergency_contact is True