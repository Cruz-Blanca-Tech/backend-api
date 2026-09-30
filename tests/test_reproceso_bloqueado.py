"""El reprocesado con IA no se puede usar sobre un expediente ya decidido.

Por qué
------
"Reprocesar Expediente (IA)" vuelve a correr el motor de triaje sobre el
expediente. Eso es una reevaluación: pisa el veredicto. Si el expediente ya fue
rechazado, se pierde la decisión; si fue aprobado, además se pierde el
beneficiario que ya se escribió en MDM.

El botón quedó deshabilitado en la UI (`canReprocess`), pero la guarda real
tiene que estar acá: la UI no es una frontera.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.contexts.data_quality_triage.application.shared.services.dossier_processor import (
    ProcessDossierUseCase,
)
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import (
    TriageStatus,
    TriageVerdict,
)
from src.core.validators.exceptions import ConflictException


def _docs():
    """Documentos del lote, ya leídos y por encima del umbral."""
    return [
        DocumentDTO(
            id=uuid4(),
            file_name="fins.jpg",
            document_code="FINS",
            extracted_data={},
            confidence_score=0.95,
        )
    ]


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


def _make_uc(existing_case, documentos=None):
    """Arma el use case con un repo que devuelve `existing_case` para el DNI.

    `documentos` simula un expediente recién subido con documentos ya leídos
    (todos por encima del umbral), que es el escenario normal del reprocesado.
    """
    repo = MagicMock()
    repo.get_by_dossier = AsyncMock(return_value=existing_case)
    repo.get_all_by_batch_id = AsyncMock(return_value=[])
    repo.save = AsyncMock()

    doc_repo = MagicMock()
    doc_repo.get_by_dni = AsyncMock(return_value=documentos or [])

    strategy = MagicMock()
    strategy.execute = AsyncMock(
        return_value=TriageCase(
            id=uuid4(),
            batch_id=existing_case.batch_id,
            activity_type="EDUCA_INSCRIPTION",
            dni_reference="12345678",
            dossier_data={},
            document_ids={},
            confidence_scores={},
            status=TriageStatus.PENDING_REVIEW,
            verdict=TriageVerdict.REQUIRES_TRIAGE,
            discrepancies=[],
        )
    )
    strategy_factory = MagicMock()
    strategy_factory.get_strategy = MagicMock(return_value=strategy)

    session = MagicMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    return ProcessDossierUseCase(
        triage_repo=repo,
        doc_repo=doc_repo,
        strategy_factory=strategy_factory,
        session=session,
    )


class TestReprocesoBloqueado:
    @pytest.mark.asyncio
    async def test_no_reprocesa_un_rechazado(self):
        existing = _make_case(TriageStatus.REJECTED)
        uc = _make_uc(existing, documentos=_docs())

        with pytest.raises(ConflictException, match="rechazado"):
            await uc.execute("12345678", existing.batch_id, "EDUCA_INSCRIPTION")

    @pytest.mark.asyncio
    async def test_no_reprocesa_un_aprobado_aunque_no_haya_llegado_al_mdm(self):
        """La decisión del revisor no se tira abajo ni con un fallo de MDM.

        Para eso está "Reintentar sincronización" en la ficha, que reintenta la
        carga sin reevaluar el expediente.
        """
        existing = _make_case(TriageStatus.APPROVED, sync_status="FAILED")
        uc = _make_uc(existing, documentos=_docs())

        with pytest.raises(ConflictException, match="aprobado"):
            await uc.execute("12345678", existing.batch_id, "EDUCA_INSCRIPTION")

    @pytest.mark.asyncio
    async def test_no_toca_el_caso_ni_lo_reconstruye_si_esta_bloqueado(self):
        """Bloqueado, el caso no se reconstruye.

        La consecuencia de que el candado esté antes de `strategy.execute()` es que
        no se llega a armar un caso nuevo, así que tampoco queda un veredicto ni
        un evento de MDM colgando de un caso que al final se descarta.
        """
        existing = _make_case(TriageStatus.REJECTED)
        uc = _make_uc(existing, documentos=_docs())

        with pytest.raises(ConflictException):
            await uc.execute("12345678", existing.batch_id, "EDUCA_INSCRIPTION")

        uc.strategy_factory.get_strategy.return_value.execute.assert_not_called()
        uc.triage_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_deja_pasar_un_expediente_pendiente(self):
        """Sin decisión previa, el reprocesado sigue disponible."""
        existing = _make_case(TriageStatus.PENDING_REVIEW)
        uc = _make_uc(existing, documentos=_docs())
        caso_nuevo = TriageCase(
            id=uuid4(),
            batch_id=existing.batch_id,
            activity_type="EDUCA_INSCRIPTION",
            dni_reference="12345678",
            dossier_data={},
            document_ids={},
            confidence_scores={},
            status=TriageStatus.PENDING_REVIEW,
            verdict=TriageVerdict.REQUIRES_TRIAGE,
            discrepancies=[],
        )
        uc.strategy_factory.get_strategy.return_value.execute = AsyncMock(
            return_value=caso_nuevo
        )
        # `session.execute` devuelve un resultado de SQLAlchemy, no un coroutine:
        # `AsyncMock` por defecto devolvería un coroutine y `fetchone()` no
        # respondería. Se arregla con un `.return_value` sincrónico.
        resultado = MagicMock()
        resultado.fetchone.return_value = None
        resultado.fetchall.return_value = []
        uc.session.execute = AsyncMock(return_value=resultado)
        # El cierre de lote abre su propia sesion; sin este mock trataria de
        # pegarle a la base de datos de verdad.
        uc.session.get = AsyncMock(return_value=None)

        import src.contexts.data_quality_triage.application.shared.services.dossier_processor as mod
        original_dispatch = mod.EventDispatcher.dispatch
        mod.EventDispatcher.dispatch = AsyncMock()
        try:
            await uc.execute("12345678", existing.batch_id, "EDUCA_INSCRIPTION")
        finally:
            mod.EventDispatcher.dispatch = original_dispatch

        assert uc.strategy_factory.get_strategy.return_value.execute.await_count == 1
