"""Cierra el lote por su cuenta, cuando todos sus expedientes ya estan decididos.

Por que existe
--------------
Habia un boton "Validar y cargar lote" que hacia tres cosas mezcladas: avisar
cuantos faltaban, sincronizar los aprobados con MDM, y poner el lote en
FINALIZED. El paso de sincronizar ya no hace falta como accion aparte: la carga
al MDM ocurre dentro de `TriageCase.approve()` (ver `DossierApprovedEvent` en
ese metodo), o sea que ocurre al decidir cada expediente.

Lo que queda es DERIVAR el estado del lote a partir de sus expedientes, sin que
nadie apriete nada:

- Si algun expediente sigue abierto -> el lote no se toca.
- Si todos estan decididos pero alguno aprobado no llego al MDM
  (`sync_status != "SYNCED"`) -> el lote queda en SYNC_FAILED esperando el
  reintento desde la ficha de ese expediente.
- Si todos estan rechazados y/o cargados en MDM -> FINALIZED.

Un lote sin ningun caso cargado tampoco se cierra: noeria cerrar un lote que
nunca se decidio.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import (
    TriageRepository,
)
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import (
    TriageStatus,
)
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import BatchStatus

logger = logging.getLogger(__name__)

# Estados en los que el expediente ya dio su veredicto y no se toca mas.
DECIDED_STATUSES = (TriageStatus.APPROVED, TriageStatus.REJECTED)

# Estados en los que el lote ya no espera cargas pendientes. Si el lote esta
# aca no hay nada que recalcular: cargar mas expedientes seria escribir sobre
# datos que el operador ya dio por cerrada.
TERMINAL_BATCH_STATUSES = (
    BatchStatus.FINALIZED,
    BatchStatus.SYNC_FAILED,
    BatchStatus.REJECTED,
    BatchStatus.FAILED,
)


def _batch_model():
    """Importa el modelo del lote de forma perezosa.

    No se puede importar arriba del módulo: `ExtractionBatchModel` declara un
    `relationship("DocumentItemModel")` resuelto por string, así que importarlo
    dispara la inicialización de los mappers y falla si `document_item_model` no
    fue importado antes. En los tests que solo exercise el dominio de triaje eso
    revienta con `InvalidRequestError: expression 'DocumentItemModel' failed to
    locate a name`.
    """
    from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import (
        ExtractionBatchModel,
    )

    return ExtractionBatchModel


class FinalizeBatchIfCompleteUseCase:
    def __init__(self, session: AsyncSession, triage_repo: TriageRepository):
        self.session = session
        self.triage_repo = triage_repo

    async def execute(self, batch_id: UUID) -> Optional[str]:
        """Devuelve el estado al que quedo el lote, o None si no cambio nada."""
        ExtractionBatchModel = _batch_model()
        lote = await self.session.get(ExtractionBatchModel, batch_id)
        if lote is None:
            logger.warning(
                "FinalizeBatchIfComplete: el lote %s no existe, no se puede cerrar.",
                batch_id,
            )
            return None

        if lote.status in TERMINAL_BATCH_STATUSES:
            # El lote ya estaba cerrado. Dejarlo como esta: reabrirlo para
            # recalcular seria resucitar un lote que el operador ya cerro.
            return None

        casos = await self.triage_repo.get_all_by_batch_id(batch_id)
        if not casos:
            # Lote sin casos: todavia no se proceso nada, no se cierra.
            return None

        abiertos = [c for c in casos if c.status not in DECIDED_STATUSES]
        if abiertos:
            logger.info(
                "Lote %s sigue abierto: %d de %d expedientes sin decidir.",
                batch_id,
                len(abiertos),
                len(casos),
            )
            return None

        # Todos decididos. Falta que los aprobados hayan llegado al MDM?
        sin_cargar = [
            c for c in casos
            if c.status == TriageStatus.APPROVED and (c.sync_status or "PENDING") != "SYNCED"
        ]

        if sin_cargar:
            detalle = ", ".join(
                f"DNI {c.dni_reference}: {c.sync_error or c.sync_status or 'sin sincronizar'}"
                for c in sin_cargar[:5]
            )
            if len(sin_cargar) > 5:
                detalle += f" (+{len(sin_cargar) - 5} mas)"
            motivo = f"{len(sin_cargar)} expediente(s) no llegaron al registro de beneficiarios: {detalle}"
            await session_update(self.session, batch_id, BatchStatus.SYNC_FAILED.value, motivo)
            logger.warning("Lote %s en SYNC_FAILED: %s", batch_id, motivo)
            return BatchStatus.SYNC_FAILED.value

        await session_update(self.session, batch_id, BatchStatus.FINALIZED.value, None)
        logger.info(
            "Lote %s FINALIZED: %d expedientes (rechazados y/o cargados en MDM).",
            batch_id,
            len(casos),
        )
        return BatchStatus.FINALIZED.value


async def session_update(session: AsyncSession, batch_id: UUID, status: str, reason: Optional[str]) -> None:
    """Actualiza el estado del lote y deja commit para quien lo llame.

    No hace commit a proposito: el lote se cierra en la misma transaccion que
    cerro el expediente que lo disparo, asi no queda un FINALIZED sin el cambio
    que lo justifico.
    """
    ExtractionBatchModel = _batch_model()
    await session.execute(
        update(ExtractionBatchModel)
        .where(ExtractionBatchModel.id == batch_id)
        .values(status=status, failure_reason=reason)
    )
