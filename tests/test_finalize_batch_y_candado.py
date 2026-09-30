"""Tests del cierre automático del lote y del candado por carga al MDM.

Contexto
--------
Había un botón "Validar y cargar lote" que sincronizaba los aprobados y ponía
el lote en FINALIZED. La sincronización ya no es un paso aparte (ocurre dentro de
`TriageCase.approve()`), así que el lote se cierra solo cuando todos sus
expedientes están rechazados y/o cargados en MDM.

Estos tests fijan esa regla y el candado que la acompaña: una vez que el
beneficiario está escrito en MDM, el expediente no se toca más desde triaje.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.contexts.data_quality_triage.application.shared.use_cases.finalize_batch_if_complete_use_case import (
    FinalizeBatchIfCompleteUseCase,
)
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.rules.dossier_status_validator import (
    DossierStatusValidator,
)
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import (
    TriageStatus,
    TriageVerdict,
)
from src.core.validators.exceptions import ConflictException


def _make_case(status, sync_status="PENDING"):
    return TriageCase(
        id=uuid4(),
        batch_id=uuid4(),
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="12345678",
        dossier_data={},
        document_ids={},
        confidence_scores={},
        status=status,
        verdict=TriageVerdict.REQUIRES_TRIAGE,
        discrepancies=[],
        sync_status=sync_status,
    )


def _make_uc(casos, batch_status="COMPLETED"):
    """Arma el use case con un lote simulado en `batch_status`."""
    session = MagicMock()
    session.execute = AsyncMock()

    lote = MagicMock()
    lote.status = batch_status
    session.get = AsyncMock(return_value=lote)

    repo = MagicMock()
    repo.get_all_by_batch_id = AsyncMock(return_value=casos)

    return FinalizeBatchIfCompleteUseCase(session=session, triage_repo=repo), session


def _params_update(session):
    """Devuelve los valores del UPDATE que el use case emitió sobre el lote.

    No se leen de los kwargs de `execute`: el `.values()` va cocido dentro del
    statement de SQLAlchemy, así que hay que compilarlo para verlos.
    """
    if not session.execute.await_args_list:
        return {}
    stmt = session.execute.await_args_list[0].args[0]
    return dict(stmt.compile().params)


def _estado_lote(session):
    return _params_update(session).get("status")


class TestFinalizeBatchSiEstaCompleto:
    @pytest.mark.asyncio
    async def test_no_cierra_si_falta_expediente_por_decidir(self):
        casos = [
            _make_case(TriageStatus.APPROVED, "SYNCED"),
            _make_case(TriageStatus.APPROVED, "SYNCED"),
            _make_case(TriageStatus.PENDING_REVIEW),
        ]
        uc, session = _make_uc(casos)

        assert await uc.execute(casos[0].batch_id) is None
        assert _estado_lote(session) is None

    @pytest.mark.asyncio
    async def test_finaliza_si_todos_estan_rechazados(self):
        casos = [
            _make_case(TriageStatus.REJECTED),
            _make_case(TriageStatus.REJECTED),
        ]
        uc, session = _make_uc(casos)

        assert await uc.execute(casos[0].batch_id) == "FINALIZED"
        assert _estado_lote(session) == "FINALIZED"

    @pytest.mark.asyncio
    async def test_finaliza_si_todos_estan_cargados_en_mdm(self):
        casos = [
            _make_case(TriageStatus.APPROVED, "SYNCED"),
            _make_case(TriageStatus.REJECTED),
            _make_case(TriageStatus.APPROVED, "SYNCED"),
        ]
        uc, session = _make_uc(casos)

        assert await uc.execute(casos[0].batch_id) == "FINALIZED"

    @pytest.mark.asyncio
    async def test_va_a_sync_failed_si_un_aprobado_no_llego_al_mdm(self):
        """Todos decididos, pero el MDM se comió uno: el lote espera."""
        casos = [
            _make_case(TriageStatus.APPROVED, "SYNCED"),
            _make_case(TriageStatus.APPROVED, "FAILED"),
        ]
        casos[1].sync_error = "conexion rehusada por el registro central"
        uc, session = _make_uc(casos)

        assert await uc.execute(casos[0].batch_id) == "SYNC_FAILED"

    @pytest.mark.asyncio
    async def test_sync_failed_incluye_el_motivo_en_el_lote(self):
        casos = [
            _make_case(TriageStatus.APPROVED, "FAILED"),
        ]
        casos[0].sync_error = "conexion rehusada"
        uc, session = _make_uc(casos)

        await uc.execute(casos[0].batch_id)

        valores = _params_update(session)
        assert "12345678" in valores["failure_reason"]
        assert "conexion rehusada" in valores["failure_reason"]

    @pytest.mark.asyncio
    async def test_no_reabre_un_lote_ya_cerrado(self):
        """Un lote en FINALIZED no se recalcula: resucitarlo escribiría sobre
        datos que el operador ya dio por cerrados."""
        casos = [_make_case(TriageStatus.APPROVED, "SYNCED")]
        uc, session = _make_uc(casos, batch_status="FINALIZED")

        assert await uc.execute(casos[0].batch_id) is None
        assert _estado_lote(session) is None

    @pytest.mark.asyncio
    async def test_no_cierra_un_lote_sin_expedientes(self):
        uc, session = _make_uc([])

        assert await uc.execute(uuid4()) is None
        assert _estado_lote(session) is None

    @pytest.mark.asyncio
    async def test_no_hace_nada_si_el_lote_no_existe(self):
        session = MagicMock()
        session.get = AsyncMock(return_value=None)
        repo = MagicMock()
        repo.get_all_by_batch_id = AsyncMock()
        uc = FinalizeBatchIfCompleteUseCase(session=session, triage_repo=repo)

        assert await uc.execute(uuid4()) is None


class TestCandadoPorCargaAlMdm:
    """La frontera de irreversibilidad es MDM, no la aprobación."""

    @pytest.fixture
    def validator(self):
        return DossierStatusValidator(batch_status_validator=None)

    @pytest.mark.asyncio
    async def test_bloquea_rechazado(self, validator):
        with pytest.raises(ConflictException, match="rechazado"):
            await validator.validate_can_be_corrected(_make_case(TriageStatus.REJECTED))

    @pytest.mark.asyncio
    async def test_bloquea_cargado_en_mdm(self, validator):
        """Este es el candado nuevo: cargado = cerrado."""
        caso = _make_case(TriageStatus.APPROVED, "SYNCED")
        with pytest.raises(ConflictException, match="registro de beneficiarios"):
            await validator.validate_can_be_corrected(caso)

    @pytest.mark.asyncio
    async def test_bloquea_rechazar_un_cargado_en_mdm(self, validator):
        """Rechazar tampoco: el beneficiario ya existe en MDM."""
        caso = _make_case(TriageStatus.APPROVED, "SYNCED")
        with pytest.raises(ConflictException, match="registro de beneficiarios"):
            await validator.validate_can_be_rejected(caso)

    @pytest.mark.asyncio
    async def test_deja_editar_aprobado_aun_no_cargado(self, validator):
        """Aprobado pero sin llegar al MDM: se puede seguir corrigiendo.

        Es el estado en el que el operador corrige un dato que el MDM rechazó, o
        reintenta si el fallo fue pasajero. Cerrar acá lo dejaría sin salida.
        """
        caso = _make_case(TriageStatus.APPROVED, "PENDING")
        await validator.validate_can_be_corrected(caso)  # no debe lanzar

    @pytest.mark.asyncio
    async def test_deja_editar_aprobado_con_mdm_fallido(self, validator):
        caso = _make_case(TriageStatus.APPROVED, "FAILED")
        await validator.validate_can_be_corrected(caso)  # no debe lanzar

    @pytest.mark.asyncio
    async def test_bloquea_si_el_lote_ya_esta_cerrado(self):
        """El candado de lote sigue vigente para un caso abierto."""
        validator_mock = MagicMock()
        validator_mock.is_batch_completed = AsyncMock(return_value=True)
        validator = DossierStatusValidator(batch_status_validator=validator_mock)

        caso = _make_case(TriageStatus.PENDING_REVIEW)
        with pytest.raises(ConflictException, match="cerrado"):
            await validator.validate_can_be_corrected(caso)

    @pytest.mark.asyncio
    async def test_deja_corregir_si_el_lote_esta_esperando_un_reintento(self):
        """`SYNC_FAILED` no es un lote cerrado: hay que poder arreglar el que falló.

        `is_batch_completed` no incluye `SYNC_FAILED`, y el frontend espeja esa
        misma lista (`LOADED_BATCH_STATUSES`). Si se los agregara, el expediente
        que no llegó al MDM quedaría bloqueado y sin forma de corregirlo: solo
        podría reintentarse, y si el MDM lo rechazó por un dato malo, el reintento
        fallaría igual.
        """
        validator_mock = MagicMock()
        validator_mock.is_batch_completed = AsyncMock(return_value=False)
        validator = DossierStatusValidator(batch_status_validator=validator_mock)

        caso = _make_case(TriageStatus.APPROVED, "FAILED")
        await validator.validate_can_be_corrected(caso)  # no debe lanzar
        await validator.validate_can_be_rejected(caso)   # no debe lanzar
