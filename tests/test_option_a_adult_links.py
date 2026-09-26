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
  5. DNI de AGRUPACIÓN del lote: si el maestro corrobora a la persona de la clave de
     agrupación con el mismo nombre, se sugiere ese DNI (evidencia documental) en
     lugar del fuzzy; si no lo corrobora, no se sugiere (verificación manual).
"""
import asyncio
import pytest
from contextlib import nullcontext
from unittest.mock import AsyncMock
from uuid import uuid4

from src.contexts.data_quality_triage.application.shared.services.beneficiary_fuzzy_matcher import (
    BeneficiaryFuzzyMatcher,
)
from src.contexts.data_quality_triage.application.shared.services.dossier_processor import (
    _ADULT_MASTER_SQL,
    _build_group_dni_suggestion as _group_dni,
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


class _SaveSessionBase:
    """`save()` también lee la fecha de nacimiento YA almacenada antes de mergear
    (invariante: la fecha del maestro no se actualiza, ver
    test_birth_date_inmutable). Por defecto la persona no tiene fecha, así que no
    interfiere con lo que prueba cada test."""

    @property
    def no_autoflush(self):
        return nullcontext()

    async def scalar(self, statement):
        return None


def _run_adult(rows, full_name, dni=None):
    session = _FakeSession(rows)
    matcher = BeneficiaryFuzzyMatcher(session)
    suggestions = asyncio.run(
        matcher.find_adult_suggestions(full_name=full_name, dni=dni, limit=3)
    )
    return suggestions, session


def test_matcher_adult_usa_type_adult_y_unica_persona_a_sugerir():
    # Maestro: una adulta "MARIA ELENA ROJAS TORRES" con DNI distinto al de la ficha.
    suggestions, session = _run_adult(
        [("ROSA LUZ", "ROJAS TORRES", "00123456")],
        full_name="MARIA ROJAS T.",
        dni="00123459",
    )
    assert session.last_params.get("ptype") == "adult"
    assert "type = :ptype" in session.last_sql
    assert len(suggestions) == 1
    assert suggestions[0].dni == "00123456"


def test_matcher_adult_dni_identico_no_sugiere_touchless():
    # Regla touchless: DNI idéntico + nombre igual/variación → match MDM, nada.
    suggestions, _ = _run_adult(
        [("ROSA LUZ", "ROJAS TORRES", "00123456")],
        full_name="MARIA ROJAS TORRES",
        dni="00123456",
    )
    assert suggestions == []


def test_matcher_adult_sin_candidato_devuelve_vacio():
    suggestions, _ = _run_adult(
        [("PEDRO", "GUTIERREZ", "99999999")],
        full_name="MARIA ROJAS",
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
            adults=[RelatedAdult(relationship="MOTHER", dni="12345678", full_name="MARIA ROJAS", phone=phone)],
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
    issues = EmergencyContactRule().evaluate(_contact_dossier(phone="900000202"))
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

    class _SeqSession(_SaveSessionBase):
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
        [_Row(id=person_id, dni="12345678", first_name="ROSA LUZ", last_name="ROJAS TORRES")],  # personas existentes por DNI
        [_Row(id=person_id, phone="900000202", role="MOTHER")],  # adults: phone, role
    ])

    # La ficha del hermano menor trae a la mamá SIN teléfono, SIN rol específico
    # y con el nombre con errores de OCR.
    adult = Adult(
        id=uuid4(),
        dni=DNI("12345678"),
        first_name="MARIA ROJAS",
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
    assert adult.phone is not None and adult.phone.value == "900000202"
    assert adult.role == RelationshipRole.MOTHER
    assert adult.first_name == "ROSA LUZ"
    assert adult.last_name == "ROJAS TORRES"


@pytest.mark.asyncio
async def test_save_actualiza_telefono_valido_de_la_ficha(monkeypatch):
    from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories import sql_beneficiary_repository as repo_mod
    from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
    from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
    from src.contexts.core_beneficiary_management.domain.entities.adult import Adult
    from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
    from src.contexts.core_beneficiary_management.domain.value_objects.phone import Phone

    person_id = uuid4()

    class _SeqSession(_SaveSessionBase):
        def __init__(self, results):
            self._results = list(results)
        async def execute(self, statement, params=None):
            return _FakeResult(self._results.pop(0))
        async def merge(self, model):
            return model
        async def commit(self):
            pass

    session = _SeqSession([
        [_Row(id=person_id, dni="12345678", first_name="ROSA LUZ", last_name="ROJAS TORRES")],
        [_Row(id=person_id, phone="900000202", role="MOTHER")],
    ])

    # La ficha SÍ aporta un teléfono válido (actualización de contacto).
    adult = Adult(
        id=uuid4(),
        dni=DNI("12345678"),
        first_name="ROSA",
        last_name="ROJAS",
    )
    adult.phone = Phone("900000203")
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

    assert adult.phone.value == "900000203"
    # El nombre siempre viene del maestro en reuso.
    assert adult.first_name == "ROSA LUZ"
    assert adult.last_name == "ROJAS TORRES"


# ------------------------- sugerencias cross-dossier y teléfono de emergencia


from src.contexts.data_quality_triage.application.shared.services.dossier_processor import (
    ProcessDossierUseCase,
    _build_emergency_phone_suggestion,
    _build_sibling_suggestions,
    _dni_valid,
    _normalize_name,
)


def test_normalize_name_y_dni_valid():
    assert _normalize_name("Maria Elena Rojas Torres") == "MARIA ELENA ROJAS TORRES"
    assert _normalize_name("  ROSA   mamani ") == "MARIA ROJAS"
    assert _normalize_name("") == ""
    assert _dni_valid("00123456") is True
    assert _dni_valid(" 00123456 ") is True
    assert _dni_valid("9847") is False
    assert _dni_valid("") is False
    assert _dni_valid(None) is False


def test_sibling_suggestions_completa_dni_y_telefono():
    index = {
        "MARIA ROJAS": [
            {"dni": "00123456", "phone": "900000202",
             "child_dni": "11111111", "child_name": "LUIS ROJAS"},
        ]
    }
    out = _build_sibling_suggestions(
        adult_index=0, ad_name="Maria Rojas", ad_dni="", ad_phone="", sibling_index=index
    )
    assert len(out) == 2
    dni_s, phone_s = out
    assert dni_s.severity == "AI_INSIGHT"
    assert dni_s.field_name == "related_adults.adults[0].dni"
    assert dni_s.expected_pattern == "00123456"
    assert "LUIS ROJAS" in dni_s.rule_description
    assert phone_s.field_name == "related_adults.adults[0].phone"
    assert phone_s.expected_pattern == "900000202"


def test_sibling_suggestions_respeta_telefono_valido_existente():
    index = {
        "MARIA ROJAS": [
            {"dni": "00123456", "phone": "900000202",
             "child_dni": "11111111", "child_name": "LUIS ROJAS"},
        ]
    }
    out = _build_sibling_suggestions(
        adult_index=0, ad_name="MARIA ROJAS", ad_dni="", ad_phone="987654321", sibling_index=index
    )
    # El DNI se sugiere, pero el teléfono ya es válido → no se toca.
    assert len(out) == 1
    assert out[0].field_name == "related_adults.adults[0].dni"


def test_sibling_suggestions_sin_dni_legible_en_hermanos_no_sugiere():
    out = _build_sibling_suggestions(
        adult_index=0,
        ad_name="MARIA ROJAS",
        ad_dni="",
        ad_phone="",
        sibling_index={"MARIA ROJAS": [{"dni": "", "phone": "", "child_dni": "1", "child_name": "X"}]},
    )
    assert out == []


def test_sibling_suggestions_dnis_conflictivos_emite_warning():
    index = {
        "MARIA ROJAS": [
            {"dni": "00123456", "phone": "900000202",
             "child_dni": "11111111", "child_name": "LUIS ROJAS"},
            {"dni": "00123458", "phone": "900000202",
             "child_dni": "22222222", "child_name": "ANA ROJAS"},
        ]
    }
    out = _build_sibling_suggestions(
        adult_index=0, ad_name="MARIA ROJAS", ad_dni="", ad_phone="", sibling_index=index
    )
    assert len(out) == 1
    assert out[0].severity == "WARNING"
    assert out[0].field_name == "related_adults.adults"
    assert "00123456" in out[0].rule_description and "00123458" in out[0].rule_description


def test_sibling_suggestions_nombre_desconocido_no_emite_nada():
    out = _build_sibling_suggestions(
        adult_index=2, ad_name="JUAN PEREZ", ad_dni="", ad_phone="", sibling_index={}
    )
    assert out == []


def test_emergency_phone_suggestion_desde_maestro():
    master = _Row(dni="00123456", first_name="ROSA", last_name="ROJAS", phone="900000202")
    out = _build_emergency_phone_suggestion(
        adult_index=1, is_emergency=True, dossier_phone="", master_row=master
    )
    assert out is not None
    assert out.severity == "AI_INSIGHT"
    assert out.field_name == "related_adults.adults[1].phone"
    assert out.expected_pattern == "900000202"
    assert "contacto de emergencia" in out.rule_description

    # No es el contacto de emergencia → nada (no se toca el teléfono de otro adulto).
    assert _build_emergency_phone_suggestion(1, False, "", master) is None
    # El teléfono del expediente ya es válido → nada.
    assert _build_emergency_phone_suggestion(1, True, "987654321", master) is None
    # El maestro tampoco tiene teléfono válido → nada.
    bad_master = _Row(dni="00123456", first_name="ROSA", last_name="ROJAS", phone="123")
    assert _build_emergency_phone_suggestion(1, True, "", bad_master) is None


class _SiblingCase:
    def __init__(self, dni_reference, dossier_data):
        self.dni_reference = dni_reference
        self.dossier_data = dossier_data


class _FakeTriageRepo:
    def __init__(self, cases):
        self.cases = cases

    async def get_all_by_batch_id(self, batch_id):
        return self.cases


def test_load_sibling_adults_indexa_y_excluye_ficha_actual():
    processor = ProcessDossierUseCase(
        triage_repo=_FakeTriageRepo([
            _SiblingCase("11111111", {
                "beneficiary": {"dni": "11111111", "first_name": "LUIS", "last_name": "ROJAS"},
                "related_adults": {
                    "adults": [{"full_name": "Maria Elena Rojas Torres", "dni": "00123456", "phone": "900000202"}],
                },
            }),
            _SiblingCase("33333333", {  # la ficha ACTUAL — debe excluirse
                "beneficiary": {"dni": "33333333", "first_name": "KAREN", "last_name": "ROJAS"},
                "related_adults": {
                    "adults": [{"full_name": "MARIA E. ROJAS", "dni": "98765432", "phone": ""}],
                },
            }),
        ]),
        doc_repo=None,
        strategy_factory=None,
        session=None,
    )

    index = asyncio.run(processor._load_sibling_adults(uuid4(), exclude_dni="33333333"))
    # Solo la ficha del hermano (LUIS) queda indexada; la actual se excluye.
    assert index == {
        "MARIA ELENA ROJAS TORRES": [
            {"dni": "00123456", "phone": "900000202",
             "child_dni": "11111111", "child_name": "LUIS ROJAS"},
        ]
    }


# --------------------------------------------- DNI de agrupación del lote


def test_sql_de_adulto_une_por_la_pk_compartida():
    """REGRESIÓN: `adults` es single-table inheritance (adults.id == persons.id).

    Con `LEFT JOIN adults a ON a.person_id = p.id` la consulta fallaba con
    UndefinedColumnError en TODA ficha que tuviera un adulto con DNI, y el
    `except Exception` del bloque de adultos se comía la excepción: en
    producción no corrían ni el touchless, ni las sugerencias de adulto, ni el
    N1, ni las sugerencias entre hermanos. Este test fija el join correcto.
    """
    sql = " ".join(_ADULT_MASTER_SQL.split()).lower()
    assert "join adults a on a.id = p.id" in sql
    assert "person_id" not in sql


def test_group_dni_sugerido_cuando_el_maestro_corrobora_el_nombre():
    # El lote agrupó con 00123456 y el maestro registra a esa persona con ese
    # nombre; el expediente trae 00123459 (OCR mal leído) → se sugiere el de agrupación.
    out = _group_dni(
        "00123456", "00123459", "ROSA LUZ", "ROJAS TORRES", ("ROSA LUZ", "ROJAS TORRES")
    )
    assert out is not None
    assert out.severity == "AI_INSIGHT"
    assert out.field_name == "beneficiary.dni"
    assert out.expected_pattern == "00123456"
    assert out.actual_value == "00123459"
    assert "00123456" in out.rule_description


def test_group_dni_sugerido_con_dni_vacio_en_la_ficha():
    out = _group_dni("00123456", "", "ROSA LUZ", "ROJAS TORRES", ("ROSA LUZ", "ROJAS TORRES"))
    assert out is not None
    assert out.expected_pattern == "00123456"
    assert out.actual_value == "(vacío)"


def test_group_dni_no_sugerido_si_el_maestro_no_conoce_el_dni():
    assert _group_dni("00123456", "00123459", "ROSA LUZ", "ROJAS", None) is None


def test_group_dni_no_sugerido_si_el_nombre_del_maestro_no_coincide():
    # Persona distinta con ese DNI → el revisor debe verificar a mano.
    assert _group_dni("00123456", "00123459", "ROSA LUZ", "ROJAS", ("PEDRO", "GUTIERREZ")) is None


def test_group_dni_no_sugerido_si_el_dni_ya_coincide():
    assert _group_dni("00123456", "00123456", "ROSA LUZ", "ROJAS", ("ROSA LUZ", "ROJAS")) is None


def test_group_dni_no_sugerido_si_el_dni_de_agrupacion_no_es_valido():
    assert _group_dni("9847", "00123459", "ROSA LUZ", "ROJAS", ("ROSA LUZ", "ROJAS")) is None
