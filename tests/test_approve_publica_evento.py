"""Tests de regresión: la aprobación debe anunciarse al maestro de beneficiarios.

Contexto de por qué existe esta suite
-------------------------------------
`TriageCase._pending_events` existe para que la aprobación de un expediente se
anuncie por el bus de eventos, y de ahí `handle_mdm_dossier_approved` carga al
beneficiario en `persons` / `beneficiary_enrollments`. La lista se inicializaba
vacía y NADA la llenaba: los 4 bucles que la despachaban iteraban siempre un
`[]`. El beneficiary solo llegaba al maestro por el atajo de
`POST /batch/{id}/verify-completion`, así que aprobar un caso no cargaba nada.

Estos tests fijan el comportamiento para que no vuelva a romperse por el camino.
"""
import pytest
from uuid import uuid4

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import (
    TriageStatus,
    TriageVerdict,
)
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import (
    FieldDiscrepancy,
)
from src.contexts.data_quality_triage.domain.shared.value_objects.quality_rule_result import (
    QualityRuleResult,
)
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent


def _make_case(status=TriageStatus.PENDING_REVIEW, dossier_data=None):
    return TriageCase(
        id=uuid4(),
        batch_id=uuid4(),
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="12345678",
        dossier_data=dossier_data if dossier_data is not None else {"beneficiary": {"dni": "12345678"}},
        document_ids={},
        confidence_scores={},
        status=status,
        verdict=TriageVerdict.REQUIRES_TRIAGE,
        discrepancies=[],
    )


class TestApproveRegistraEvento:
    def test_approve_manual_registra_un_evento(self):
        case = _make_case()
        user_id = uuid4()

        case.approve(user_id)

        eventos = case.pending_events
        assert len(eventos) == 1
        assert isinstance(eventos[0], DossierApprovedEvent)
        assert eventos[0].triage_case_id == case.id
        assert eventos[0].batch_id == case.batch_id
        assert eventos[0].dni_reference == "12345678"
        assert eventos[0].approved_by == user_id

    def test_approve_touchless_usa_actor_sintetico(self):
        case = _make_case()

        case.approve(None)

        assert len(case.pending_events) == 1
        assert case.verdict == TriageVerdict.AUTO_APPROVED
        # Sin usuario no hay a quién atribuirlo, pero el campo es obligatorio.
        assert case.pending_events[0].approved_by is not None

    def test_approve_registra_snapshot_del_dossier(self):
        """El evento debe llevar una COPIA: la capa de aplicación sigue
        mutando el caso después de aprobar y el bus se despacha más tarde."""
        case = _make_case(dossier_data={"beneficiary": {"dni": "12345678"}})
        case.approve(uuid4())

        case.dossier_data["beneficiary"]["dni"] = "99999999"

        assert case.pending_events[0].dossier_data["beneficiary"]["dni"] == "12345678"


class TestApproveSellaTimestamps:
    def test_approve_registra_completed_at(self):
        """Sin completed_at, el export de tesis deja el tiempo vacío
        justamente en los casos automáticos, que son los que interesan medir."""
        case = _make_case()
        assert case.completed_at is None

        case.approve(None)

        assert case.completed_at is not None
        assert case.resolved_at is not None
        assert case.resolved_at == case.completed_at


class TestApproveNoDuplicaEvento:
    def test_segunda_aprobacion_no_publica_dos_veces(self):
        """Sin este guard, `create_from_quality_result` y el caso 6 de la tabla
        DNI pueden aprobar el mismo caso y sincronizar dos veces."""
        case = _make_case()

        case.approve(None)
        case.approve(None)

        assert len(case.pending_events) == 1

    def test_clear_events_vacia_la_cola(self):
        case = _make_case()
        case.approve(uuid4())

        case.clear_events()

        assert case.pending_events == []


class TestReassignIdRekeyeaElEvento:
    def test_reassign_id_actualiza_el_id_del_evento(self):
        """Al reprocesar, `dossier_processor` re-keyea el caso al id existente.
        Si el evento no se rehace, el handler de MDM corre su
        `UPDATE sync_status` sobre un id inexistente: 0 filas, sin error, y el
        beneficiario queda cargado con el caso en PENDING para siempre."""
        case = _make_case()
        case.approve(None)
        id_original = case.id
        id_real = uuid4()

        case.reassign_id(id_real)

        assert case.id == id_real
        assert len(case.pending_events) == 1
        assert case.pending_events[0].triage_case_id == id_real
        assert case.pending_events[0].triage_case_id != id_original

    def test_reassign_id_conserva_el_resto_del_evento(self):
        case = _make_case()
        user_id = uuid4()
        case.approve(user_id)
        original = case.pending_events[0]

        case.reassign_id(uuid4())
        rehecho = case.pending_events[0]

        assert rehecho.batch_id == original.batch_id
        assert rehecho.activity_type == original.activity_type
        assert rehecho.dni_reference == original.dni_reference
        assert rehecho.approved_by == user_id
        assert rehecho.dossier_data == original.dossier_data


class TestCreateFromQualityResultRutaTouchless:
    def _quality_result(self, is_valid, discrepancies=None):
        return QualityRuleResult(
            is_valid=is_valid,
            discrepancies=discrepancies or [],
        )

    def test_touchless_pasa_por_approve_y_sella_completed_at(self):
        """La ruta touchless seteaba APPROVED en el constructor y se saltaba
        `approve()`: completed_at/resolved_at quedaban en None y no se
        registraba el evento, así que el beneficiario no se cargaba."""
        case = TriageCase.create_from_quality_result(
            batch_id=uuid4(),
            activity_type="EDUCA_INSCRIPTION",
            dni_reference="12345678",
            documents=[],
            quality_result=self._quality_result(is_valid=True),
            dossier_data={"beneficiary": {"dni": "12345678"}},
        )

        assert case.status == TriageStatus.APPROVED
        assert case.verdict == TriageVerdict.AUTO_APPROVED
        assert case.completed_at is not None
        assert len(case.pending_events) == 1
        assert isinstance(case.pending_events[0], DossierApprovedEvent)

    def test_caso_con_errores_no_aprueba_ni_publica(self):
        disc = FieldDiscrepancy(
            field_name="beneficiary.dni",
            expected_pattern="DNI",
            actual_value="(vacío)",
            rule_description="Falta el DNI",
            severity="ERROR",
            document_code="DOMINIO",
        )
        resultado = self._quality_result(is_valid=False, discrepancies=[disc])

        case = TriageCase.create_from_quality_result(
            batch_id=uuid4(),
            activity_type="EDUCA_INSCRIPTION",
            dni_reference="12345678",
            documents=[],
            quality_result=resultado,
            dossier_data={},
        )

        assert case.status != TriageStatus.APPROVED
        assert case.pending_events == []
