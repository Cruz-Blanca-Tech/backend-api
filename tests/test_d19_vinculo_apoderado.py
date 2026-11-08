"""D19: parentesco, apoderado y contacto de emergencia se guardan en el vínculo niño-adulto."""
from uuid import uuid4

import pytest

from src.contexts.core_beneficiary_management.domain.entities.adult import Adult
from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
from src.contexts.core_beneficiary_management.domain.value_objects.relationship_role import RelationshipRole
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Session:
    def __init__(self, rows=None):
        self.statements = []
        self._rows = rows or []

    async def execute(self, statement, params=None):
        self.statements.append(statement)
        return _Result(self._rows)


def _beneficiary(dni, adults):
    return Beneficiary(id=uuid4(), dni=DNI(dni), first_name="NIÑO", last_name="PRUEBA", relatives=adults)


def _adult(dni, role, guardian=False, emergency=False):
    return Adult(id=uuid4(), dni=DNI(dni), first_name="ADULTO", last_name="PRUEBA",
                 role=role, is_guardian=guardian, is_emergency_contact=emergency)


@pytest.mark.asyncio
async def test_save_escribe_parentesco_y_marcas_en_el_vinculo():
    madre = _adult("87654321", RelationshipRole.MOTHER, guardian=True, emergency=True)
    hijo = _beneficiary("12345678", [madre])
    session = _Session()
    await SqlBeneficiaryRepository(session)._write_link_flags(hijo)

    assert len(session.statements) == 1
    values = {c.key: v.value for c, v in session.statements[0]._values.items()}
    assert values == {"relationship_type": "MOTHER", "is_guardian": True, "is_emergency_contact": True}


@pytest.mark.asyncio
async def test_hermanos_con_apoderados_distintos():
    """El padre es apoderado de un hermano y la madre del otro: cada niño conserva el suyo."""
    padre = _adult("11111111", RelationshipRole.FATHER)
    madre = _adult("22222222", RelationshipRole.MOTHER)
    hermano_a = _beneficiary("33333333", [padre, madre])
    hermano_b = _beneficiary("44444444", [Adult(**{**padre.__dict__}), Adult(**{**madre.__dict__})])
    # Marca heredada del adulto (último guardado): madre apoderada de los dos.
    for b in (hermano_a, hermano_b):
        b.relatives[0].is_guardian = False
        b.relatives[1].is_guardian = True

    links = [
        (hermano_a.id, padre.id, True, False),
        (hermano_a.id, madre.id, False, False),
        (hermano_b.id, padre.id, False, False),
        (hermano_b.id, madre.id, True, False),
    ]
    await SqlBeneficiaryRepository(_Session(links))._apply_link_flags([hermano_a, hermano_b])

    assert [a.is_guardian for a in hermano_a.relatives] == [True, False]
    assert [a.is_guardian for a in hermano_b.relatives] == [False, True]


@pytest.mark.asyncio
async def test_vinculo_antiguo_sin_marca_conserva_la_del_adulto():
    madre = _adult("22222222", RelationshipRole.MOTHER, guardian=True)
    hijo = _beneficiary("33333333", [madre])
    await SqlBeneficiaryRepository(_Session([(hijo.id, madre.id, None, None)]))._apply_link_flags([hijo])
    assert hijo.relatives[0].is_guardian is True
