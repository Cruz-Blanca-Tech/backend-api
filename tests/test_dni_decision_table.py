"""Tabla de decisión DNI del beneficiario — crosscheck entre documentos y touchless.

Cubre los 6 casos acordados con el operador:

  1. Todas las lecturas válidas coinciden                     → touchless (nada que hacer).
  2. FINS sin DNI válido + 2+ documentos válidos coinciden     → AI_INSIGHT "CORROBORATED"
     (precarga del candidato; el operador confirma con 1 clic).
  3. Lecturas válidas difieren por 1 dígito (fuzzy)            → WARNING visible + propuesta
     del mayoritario (AI_INSIGHT); nunca auto-cerrar.
  4. Difieren por varios dígitos                               → ERROR (el operador resuelve).
  5. Ningún documento con DNI válido                           → nada aquí: la regla de
     completitud ya emite el ERROR "DNI obligatorio".
  6. El candidato existe en el maestro MDM y calza nombre + fecha
     de nacimiento                                            → TOUCHLESS (se aplica solo;
     el caso queda APPROVED sin intervención).
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from src.contexts.data_quality_triage.domain.educa.rules.document.dni_rules import (
    BeneficiaryDniCrosscheckRule,
)
from src.contexts.data_quality_triage.domain.shared.value_objects.enriched_field import EnrichedField
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.application.shared.services.dossier_processor import ProcessDossierUseCase


def _field(name, raw, normalized):
    return EnrichedField(name=name, raw_value=raw, normalized_value=normalized)


def _valid_dni(value: str) -> EnrichedField:
    return EnrichedField(name="Número de Documento", raw_value=value, normalized_value=value)


def _invalid_dni(value: str) -> EnrichedField:
    # 9 dígitos (o con caracteres raros) → no se normaliza → campo inválido.
    return EnrichedField(name="Número de Documento", raw_value=value, normalized_value=None)


def _birth(value: str):
    """Simula la fecha de nacimiento del maestro (date en Postgres)."""
    from datetime import date

    return date.fromisoformat(value)


def _rule() -> BeneficiaryDniCrosscheckRule:
    return BeneficiaryDniCrosscheckRule()


# --------------------------------------------------------------- casos 1 y 2


def test_caso_1_todas_las_lecturas_coinciden_no_emite_nada():
    rule = _rule()
    fins = SimpleNamespace(child_dni=_valid_dni("90020720"))
    dj = SimpleNamespace(child_dni=_valid_dni("90020720"))
    dnibe = SimpleNamespace(document_number=_valid_dni("90020720"))
    assert rule.evaluate(enriched_fins=fins, enriched_dj=dj, enriched_dnibe=dnibe) == []


def test_caso_2_fins_invalido_pero_dj_y_dnibe_coinciden_sugiere_el_dni():
    """Caso real 900220720: FINS leyó 9 dígitos; DJ y DNIBE coinciden en 90020720."""
    rule = _rule()
    fins = SimpleNamespace(child_dni=_invalid_dni("900220720"))
    dj = SimpleNamespace(child_dni=_valid_dni("90020720"))
    dnibe = SimpleNamespace(document_number=_valid_dni("90020720"))
    out = rule.evaluate(enriched_fins=fins, enriched_dj=dj, enriched_dnibe=dnibe)
    assert len(out) == 1
    d = out[0]
    assert d.severity == "AI_INSIGHT"
    assert d.field_name == "beneficiary.dni"
    assert d.expected_pattern == "90020720"
    assert d.document_code == BeneficiaryDniCrosscheckRule.CORROBORATION_DOC


def test_caso_2_sin_fins_pero_dos_validos_coinciden_sugiere():
    rule = _rule()
    dj = SimpleNamespace(child_dni=_valid_dni("90020720"))
    dnibe = SimpleNamespace(document_number=_valid_dni("90020720"))
    out = rule.evaluate(enriched_dj=dj, enriched_dnibe=dnibe)
    assert len(out) == 1
    assert out[0].expected_pattern == "90020720"


def test_caso_2_solo_un_documento_valido_no_sugiere():
    # Una sola lectura válida no es corroboración entre documentos.
    rule = _rule()
    dj = SimpleNamespace(child_dni=_valid_dni("90020720"))
    dnibe = SimpleNamespace(document_number=_invalid_dni("900220720"))
    assert rule.evaluate(enriched_dj=dj, enriched_dnibe=dnibe) == []


# --------------------------------------------------------------- caso 3 (fuzzy)


def test_caso_3_diferencia_de_un_digito_con_mayoria_propone_y_advierte():
    rule = _rule()
    fins = SimpleNamespace(child_dni=_valid_dni("90020720"))
    dj = SimpleNamespace(child_dni=_valid_dni("90020720"))
    dnibe = SimpleNamespace(document_number=_valid_dni("90020721"))  # 1 dígito distinto
    out = rule.evaluate(enriched_fins=fins, enriched_dj=dj, enriched_dnibe=dnibe)
    severities = sorted(d.severity for d in out)
    assert severities == ["AI_INSIGHT", "WARNING"]
    warning = next(d for d in out if d.severity == "WARNING")
    insight = next(d for d in out if d.severity == "AI_INSIGHT")
    assert warning.field_name == "beneficiary_dni_crosscheck"
    assert insight.field_name == "beneficiary.dni"
    # Propuesta del mayoritario (2 lecturas 90020720 vs 1 lectura 90020721).
    assert insight.expected_pattern == "90020720"
    assert insight.document_code == BeneficiaryDniCrosscheckRule.CORROBORATION_DOC


def test_caso_3_diferencia_de_un_digito_sin_mayoria_solo_advierte():
    # Empate 1-1: no hay mayoritario → solo la advertencia visible, nunca auto.
    rule = _rule()
    dj = SimpleNamespace(child_dni=_valid_dni("90020720"))
    dnibe = SimpleNamespace(document_number=_valid_dni("90020721"))
    out = rule.evaluate(enriched_dj=dj, enriched_dnibe=dnibe)
    assert len(out) == 1
    assert out[0].severity == "WARNING"
    assert out[0].field_name == "beneficiary_dni_crosscheck"


# --------------------------------------------------------------- caso 4 (ERROR)


def test_caso_4_varios_digitos_distintos_emite_error():
    rule = _rule()
    dj = SimpleNamespace(child_dni=_valid_dni("90020720"))
    dnibe = SimpleNamespace(document_number=_valid_dni("41188210"))  # difiere en varios
    out = rule.evaluate(enriched_dj=dj, enriched_dnibe=dnibe)
    assert len(out) == 1
    assert out[0].severity == "ERROR"
    assert out[0].field_name == "beneficiary_dni_crosscheck"


# --------------------------------------------------------------- caso 5 (vacío)


def test_caso_5_ningun_dni_valido_no_emite_nada_aqui():
    # La completitud (BeneficiaryCompletenessRule) emite el ERROR de DNI obligatorio.
    rule = _rule()
    fins = SimpleNamespace(child_dni=_invalid_dni("900220720"))
    dj = SimpleNamespace(child_dni=_invalid_dni("900220720"))
    dnibe = SimpleNamespace(document_number=_invalid_dni("900220720"))
    assert rule.evaluate(enriched_fins=fins, enriched_dj=dj, enriched_dnibe=dnibe) == []


# --------------------------------------------------------------- caso 6 (touchless)


def _case(dossier, discrepancies):
    return TriageCase(
        id=uuid4(),
        batch_id=uuid4(),
        activity_type="EDUCA_INSCRIPTION",
        dni_reference=dossier["beneficiary"]["dni"],
        dossier_data=dossier,
        document_ids={},
        confidence_scores={},
        status=TriageStatus.PENDING_REVIEW,
        verdict=TriageVerdict.REQUIRES_TRIAGE,
        discrepancies=discrepancies,
    )


class _CorrobSession:
    """Sesión fake: devuelve una fila del maestro (persona con ese DNI)."""

    def __init__(self, master_row):
        self._master_row = master_row
        self.added_objects = []

    def add(self, obj):
        self.added_objects.append(obj)

    async def execute(self, statement, params=None):
        class _Result:
            def __init__(self, row):
                self._row = row

            def fetchone(self):
                return self._row

        return _Result(self._master_row)


def _processor_with(session) -> ProcessDossierUseCase:
    return ProcessDossierUseCase(
        triage_repo=AsyncMock(),
        doc_repo=AsyncMock(),
        strategy_factory=AsyncMock(),
        session=session,
    )


def _run(coro):
    import asyncio

    return asyncio.run(coro)


def test_caso_6_maestro_corroba_nombre_y_fecha_touchless_aprueba():
    candidate = "90020720"
    dossier = {
        "beneficiary": {
            "dni": "(vacío)",
            "first_name": "AYLEN",
            "last_name": "ESPINOZA JAIMES",
            "birth_date": "2016-05-10",
        }
    }
    discrepancies = [
        FieldDiscrepancy(
            field_name="beneficiary.dni",
            expected_pattern="El DNI del beneficiario es obligatorio",
            actual_value="(vacío)",
            rule_description="El DNI del beneficiario es obligatorio.",
            severity="ERROR",
        ),
        # El insight de corroboración que emite la regla de crosscheck (caso 2).
        FieldDiscrepancy(
            field_name="beneficiary.dni",
            expected_pattern=candidate,
            actual_value="(vacío)",
            rule_description="La ficha FINS no trae un DNI legible…",
            severity="AI_INSIGHT",
            document_code=BeneficiaryDniCrosscheckRule.CORROBORATION_DOC,
        ),
    ]
    case = _case(dossier, discrepancies)
    # El maestro registra a AYLEN ESPINOZA JAIMES (nombre calza) con su fecha de
    # nacimiento y el DNI candidato.
    master_row = ("AYLEN", "ESPINOZA JAIMES", _birth("2016-05-10"))

    processor = _processor_with(_CorrobSession(master_row))
    applied = _run(processor._apply_corroborated_dni_touchless(case, "AYLEN", "ESPINOZA JAIMES"))

    assert applied == candidate
    assert case.dossier_data["beneficiary"]["dni"] == candidate
    # Quedó touchless APPROVED (sin errores ni warnings).
    assert case.status == TriageStatus.APPROVED
    assert case.verdict == TriageVerdict.AUTO_APPROVED
    # La única discrepancia restante es la nota interna INFO (no se muestra).
    assert [d.severity for d in case.discrepancies] == ["INFO"]


def test_caso_6_maestro_no_conoce_el_dni_no_aplica_y_conserva_insight():
    candidate = "90020720"
    dossier = {
        "beneficiary": {
            "dni": "(vacío)",
            "first_name": "AYLEN",
            "last_name": "ESPINOZA JAIMES",
            "birth_date": "2016-05-10",
        }
    }
    discrepancies = [
        FieldDiscrepancy(
            field_name="beneficiary.dni",
            expected_pattern=candidate,
            actual_value="(vacío)",
            rule_description="La ficha FINS no trae un DNI legible…",
            severity="AI_INSIGHT",
            document_code=BeneficiaryDniCrosscheckRule.CORROBORATION_DOC,
        ),
    ]
    case = _case(dossier, discrepancies)

    processor = _processor_with(_CorrobSession(None))  # el maestro no conoce ese DNI
    applied = _run(processor._apply_corroborated_dni_touchless(case, "AYLEN", "ESPINOZA JAIMES"))

    assert applied is None
    assert case.status == TriageStatus.PENDING_REVIEW
    # El AI_INSIGHT queda disponible para el operador (confirmar con 1 clic).
    assert any(d.severity == "AI_INSIGHT" for d in case.discrepancies)


def test_caso_6_nombre_distinto_en_el_maestro_no_aplica():
    dossier = {
        "beneficiary": {
            "dni": "(vacío)",
            "first_name": "AYLEN",
            "last_name": "ESPINOZA JAIMES",
            "birth_date": "2016-05-10",
        }
    }
    discrepancies = [
        FieldDiscrepancy(
            field_name="beneficiary.dni",
            expected_pattern="90020720",
            actual_value="(vacío)",
            rule_description="La ficha FINS no trae un DNI legible…",
            severity="AI_INSIGHT",
            document_code=BeneficiaryDniCrosscheckRule.CORROBORATION_DOC,
        ),
    ]
    case = _case(dossier, discrepancies)
    # El maestro tiene OTRA persona con ese DNI (homónimo falso).
    master_row = ("PEDRO", "GUTIERREZ", _birth("2016-05-10"))

    processor = _processor_with(_CorrobSession(master_row))
    applied = _run(processor._apply_corroborated_dni_touchless(case, "AYLEN", "ESPINOZA JAIMES"))

    assert applied is None
    assert any(d.severity == "AI_INSIGHT" for d in case.discrepancies)


def test_caso_6_fecha_de_nacimiento_distinta_no_aplica():
    dossier = {
        "beneficiary": {
            "dni": "(vacío)",
            "first_name": "AYLEN",
            "last_name": "ESPINOZA JAIMES",
            "birth_date": "2016-05-10",
        }
    }
    discrepancies = [
        FieldDiscrepancy(
            field_name="beneficiary.dni",
            expected_pattern="90020720",
            actual_value="(vacío)",
            rule_description="La ficha FINS no trae un DNI legible…",
            severity="AI_INSIGHT",
            document_code=BeneficiaryDniCrosscheckRule.CORROBORATION_DOC,
        ),
    ]
    case = _case(dossier, discrepancies)
    # Mismo nombre pero fecha de nacimiento distinta → no es la misma persona.
    master_row = ("AYLEN", "ESPINOZA JAIMES", _birth("2010-01-01"))

    processor = _processor_with(_CorrobSession(master_row))
    applied = _run(processor._apply_corroborated_dni_touchless(case, "AYLEN", "ESPINOZA JAIMES"))

    assert applied is None
    assert any(d.severity == "AI_INSIGHT" for d in case.discrepancies)


def test_caso_6_fecha_calza_si_alguna_falta_y_nombre_coincide():
    # Si el expediente no trae fecha (OCR), alcanza con el nombre corroborado.
    dossier = {
        "beneficiary": {
            "dni": "(vacío)",
            "first_name": "AYLEN",
            "last_name": "ESPINOZA JAIMES",
            "birth_date": "",
        }
    }
    discrepancies = [
        FieldDiscrepancy(
            field_name="beneficiary.dni",
            expected_pattern="90020720",
            actual_value="(vacío)",
            rule_description="La ficha FINS no trae un DNI legible…",
            severity="AI_INSIGHT",
            document_code=BeneficiaryDniCrosscheckRule.CORROBORATION_DOC,
        ),
    ]
    case = _case(dossier, discrepancies)
    master_row = ("AYLEN", "ESPINOZA JAIMES", None)

    processor = _processor_with(_CorrobSession(master_row))
    applied = _run(processor._apply_corroborated_dni_touchless(case, "AYLEN", "ESPINOZA JAIMES"))

    assert applied == "90020720"
    assert case.status == TriageStatus.APPROVED