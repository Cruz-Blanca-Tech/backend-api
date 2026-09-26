"""Opción A — vínculo de adultos/apoderados con el maestro.

Cubre:
  1. Matcher fuzzy de ADULTOS (type='adult'): regla touchless — DNI idéntico a
     un adulto existente NO genera sugerencia; DNI distinto + nombre similar SÍ.
  2. EmergencyContactRule: el contacto de emergencia exige teléfono VÁLIDO
     (vacío o formato raro → ERROR bloqueante). Adultos no-emergencia no aplican.
  3. sql_beneficiary_repository.save: al reusar un adulto del maestro, se
     conserva su teléfono/rol cuando la ficha no aporta datos válidos.
  4. Ambigüedad de coincidencia (N1): con 3+ candidatos o dos casi empatados la
     sugerencia se eleva a WARNING ("verifique si el adulto ya existe") en vez de
     proponer un vínculo a ciegas.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.contexts.data_quality_triage.application.shared.services.beneficiary_fuzzy_matcher import (
    BeneficiaryFuzzyMatcher,
)
from src.contexts.data_quality_triage.domain.educa.rules.domain.family_rules import EmergencyContactRule
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData
from src.contexts.data_quality_triage.domain.educa.value_objects.religion_data import ReligionData
from src.contexts.data_quality_triage.domain.educa.value_objects.permissions_data import PermissionsData
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult


# ---------------------------------------------------------------- fuzzy ADULT


class _FakeResult:
    def __init__(self, rows, captured=None):
        self._rows = rows
        self._captured = captured

    def fetchall(self):
        return list(self._rows)

    def all(self):
        return list(self._rows)


class _Row:
    """Fila SQL falsa con acceso por atributo (row.dni, row.id, row.phone...)."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.last_params = None
        self.last_sql = None

    async def execute(self, statement, params=None):
        self.last_sql = str(statement)
        self.last_params = params
        return _FakeResult(self._rows)


def _run_adult(rows, full_name, dni=None):
    session = _FakeSession(rows)
    matcher = BeneficiaryFuzzyMatcher(session)
    suggestions = asyncio.run(
        matcher.find_adult_suggestions(full_name=full_name, dni=dni, limit=3)
    )
    return suggestions, session


def test_matcher_adult_usa_type_adult_y_unica_persona_a_sugerir():
    # Maestro: una adulta "ROSA LUZ MAMANI CONDORI" con DNI distinto al de la ficha.
    suggestions, session = _run_adult(
        [("ROSA LUZ", "MAMANI CONDORI", "09847291")],
        full_name="ROSA MAMANI C.",
        dni="09847299",
    )
    assert session.last_params.get("ptype") == "adult"
    assert "type = :ptype" in session.last_sql
    assert len(suggestions) == 1
    assert suggestions[0].dni == "09847291"


def test_matcher_adult_dni_identico_no_sugiere_touchless():
    # Regla touchless: DNI idéntico + nombre igual/variación → match MDM, nada.
    suggestions, _ = _run_adult(
        [("ROSA LUZ", "MAMANI CONDORI", "09847291")],
        full_name="ROSA MAMANI CONDORI",
        dni="09847291",
    )
    assert suggestions == []


def test_matcher_adult_sin_candidato_devuelve_vacio():
    suggestions, _ = _run_adult(
        [("PEDRO", "GUTIERREZ", "99999999")],
        full_name="ROSA MAMANI",
        dni="11111111",
    )
    assert suggestions == []


# --------------------------------------------- ambigüedad de coincidencia (N1)


from src.contexts.data_quality_triage.application.shared.services.dossier_processor import (
    _adult_match_is_ambiguous,
    _AMBIGUITY_GAP,
)


def _sug(score):
    return _Row(score=score, first_name="X", last_name="Y", dni="12345678")


def test_adult_match_3_candidatos_es_ambiguo():
    # Demasiadas coincidencias (top-3 completo) → no se sugiere, se advierte.
    assert _adult_match_is_ambiguous([_sug(0.90), _sug(0.60), _sug(0.55)]) is True


def test_adult_match_dos_candidatos_empatados_es_ambiguo():
    # Sin ganador claro: el segundo está casi al nivel del primero.
    assert _adult_match_is_ambiguous([_sug(0.72), _sug(0.65)]) is True
    assert _AMBIGUITY_GAP == 0.10


def test_adult_match_dos_candidatos_con_top_dominante_no_es_ambiguo():
    # Gap amplio → se puede sugerir con confianza.
    assert _adult_match_is_ambiguous([_sug(0.95), _sug(0.60)]) is False


def test_adult_match_un_candidato_unico_no_es_ambiguo():
    assert _adult_match_is_ambiguous([_sug(0.70)]) is False


# ---------------------------------------------------- EmergencyContactRule


def _contact_dossier(phone):
    return EducaInscriptionDossier(
        beneficiary=BeneficiaryData(),
        related_adults=FamilyData(
            adults=[RelatedAdult(relationship="MOTHER", dni="12345678", full_name="ROSA MAMANI", phone=phone)],
            emergency_contact_dni="12345678",
        ),
        education=EducationData(),
        medical=MedicalData(),
        religion=ReligionData(),
        permissions=PermissionsData(),
    )


def test_emergency_contact_requiere_telefono():
    issues = EmergencyContactRule().evaluate(_contact_dossier(phone=None))
    assert any(i.severity == "ERROR" and "teléfono" in i.rule_description for i in issues)


def test_emergency_contact_rechaza_telefono_invalido():
    issues = EmergencyContactRule().evaluate(_contact_dossier(phone="123"))
    assert any(i.severity == "ERROR" and "teléfono" in i.rule_description for i in issues)


def test_emergency_contact_acepta_telefono_valido():
    issues = EmergencyContactRule().evaluate(_contact_dossier(phone="925917655"))
    assert not any(i.severity == "ERROR" and "teléfono" in i.rule_description for i in issues)


# ------------------------------------- preservación en reuso (repo save)


@pytest.mark.asyncio
async def test_save_preserva_telefono_y_rol_del_maestro_en_reuso(monkeypatch):
    from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories import sql_beneficiary_repository as repo_mod
    from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
    from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
    from src.contexts.core_beneficiary_management.domain.entities.adult import Adult
    from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
    from src.contexts.core_beneficiary_management.domain.value_objects.relationship_role import RelationshipRole

    person_id = uuid4()

    class _SeqSession:
        """Devuelve la respuesta de persons primero y la de adults después."""
        def __init__(self, results):
            self._results = list(results)
            self.calls = 0
        async def execute(self, statement, params=None):
            self.calls += 1
            return _FakeResult(self._results.pop(0))
        async def merge(self, model):
            return model
        async def commit(self):
            pass

    session = _SeqSession([
        [_Row(id=person_id, dni="12345678", first_name="ROSA LUZ", last_name="MAMANI CONDORI")],  # personas existentes por DNI
        [_Row(id=person_id, phone="925917655", role="MOTHER")],  # adults: phone, role
    ])

    # La ficha del hermano menor trae a la mamá SIN teléfono, SIN rol específico
    # y con el nombre con errores de OCR.
    adult = Adult(
        id=uuid4(),
        dni=DNI("12345678"),
        first_name="ROSA MAMANI",
        last_name="C",
        role=RelationshipRole.OTHER,
        phone=None,
    )
    ben = Beneficiary(
        id=uuid4(),
        dni=DNI("87654321"),
        first_name="HERMANO",
        last_name="MENOR",
        relatives=[adult],
    )

    # No queremos probar el mapeo SQLAlchemy completo: solo la lógica del save.
    monkeypatch.setattr(
        repo_mod.BeneficiaryMapper,
        "to_persistence",
        staticmethod(lambda b: "model-fake"),
    )

    repo = SqlBeneficiaryRepository(session=session)
    await repo.save(ben)

    # El adulto reusó el id del maestro y conservó su TELÉFONO, su ROL y su NOMBRE.
    assert adult.id == person_id
    assert adult.phone is not None and adult.phone.value == "925917655"
    assert adult.role == RelationshipRole.MOTHER
    assert adult.first_name == "ROSA LUZ"
    assert adult.last_name == "MAMANI CONDORI"


@pytest.mark.asyncio
async def test_save_actualiza_telefono_valido_de_la_ficha(monkeypatch):
    from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories import sql_beneficiary_repository as repo_mod
    from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
    from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
    from src.contexts.core_beneficiary_management.domain.entities.adult import Adult
    from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
    from src.contexts.core_beneficiary_management.domain.value_objects.phone import Phone

    person_id = uuid4()

    class _SeqSession:
        def __init__(self, results):
            self._results = list(results)
        async def execute(self, statement, params=None):
            return _FakeResult(self._results.pop(0))
        async def merge(self, model):
            return model
        async def commit(self):
            pass

    session = _SeqSession([
        [_Row(id=person_id, dni="12345678", first_name="ROSA LUZ", last_name="MAMANI CONDORI")],
        [_Row(id=person_id, phone="925917655", role="MOTHER")],
    ])

    # La ficha SÍ aporta un teléfono válido (actualización de contacto).
    adult = Adult(
        id=uuid4(),
        dni=DNI("12345678"),
        first_name="ROSA",
        last_name="MAMANI",
    )
    adult.phone = Phone("997230421")
    ben = Beneficiary(
        id=uuid4(),
        dni=DNI("87654321"),
        first_name="HERMANO",
        last_name="MENOR",
        relatives=[adult],
    )

    monkeypatch.setattr(
        repo_mod.BeneficiaryMapper,
        "to_persistence",
        staticmethod(lambda b: "model-fake"),
    )

    repo = SqlBeneficiaryRepository(session=session)
    await repo.save(ben)

    assert adult.phone.value == "997230421"
    # El nombre siempre viene del maestro en reuso.
    assert adult.first_name == "ROSA LUZ"
    assert adult.last_name == "MAMANI CONDORI"