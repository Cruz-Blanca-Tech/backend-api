from typing import Optional
from uuid import UUID

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.ports.batch_status_validator import BatchStatusValidatorPort
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
from src.core.validators.exceptions import ConflictException


class DossierStatusValidator:
    """
    Regla de dominio unificada para verificar si un expediente de triaje y su lote asociado
    se encuentran en un estado que admita modificaciones (corrección o rechazo).
    """

    def __init__(self, batch_status_validator: Optional[BatchStatusValidatorPort] = None):
        self.batch_status_validator = batch_status_validator

    async def validate_can_be_corrected(self, case: TriageCase) -> None:
        """
        Valida que el expediente pueda ser corregido.
        Lanza ConflictException si el lote al que pertenece ya fue cerrado, o si el
        expediente ya está rechazado, o si ya llegó al registro de beneficiarios.
        """
        await self._validate_batch_not_completed(case.batch_id, action="correcciones")
        if case.status == TriageStatus.REJECTED:
            raise ConflictException(
                "El expediente ya se encuentra rechazado y no admite más correcciones."
            )
        self._validate_not_loaded(case, action="correcciones")

    async def validate_can_be_rejected(self, case: TriageCase) -> None:
        """
        Valida que el expediente pueda ser rechazado.
        Lanza ConflictException si el lote al que pertenece ya fue cerrado, o si el
        expediente ya está rechazado, o si ya llegó al registro de beneficiarios.
        """
        await self._validate_batch_not_completed(case.batch_id, action="rechazos")
        if case.status == TriageStatus.REJECTED:
            raise ConflictException(
                "El expediente ya se encuentra rechazado y no admite más rechazos."
            )
        self._validate_not_loaded(case, action="rechazos")

    def _validate_not_loaded(self, case: TriageCase, action: str) -> None:
        """Bloquea cuando el expediente ya está escrito en MDM.

        La frontera de irreversibilidad es la carga al registro de beneficiarios,
        no la aprobación: aprobar por sí solo no cierra nada (la carga es
        sincrónica y si falla el caso queda en `sync_status="FAILED"`, editable y
        reintentable). Lo que cierra el expediente es que el beneficiario ya
        exista en MDM.

        Mientras no se haya cargado, un `APPROVED` se sigue admitiendo a
        propósito: es el estado en el que el operador puede corregir los datos y
        volver a validar si la carga falló por un dato malo, y en el que puede
        apretar "Reintentar sincronización" si fue un fallo pasajero.
        """
        if (case.sync_status or "") == "SYNCED":
            raise ConflictException(
                "Este expediente ya está cargado en el registro de beneficiarios y no admite más "
                f"{action} desde triaje. Si algún dato está mal, corríalo en la ficha del beneficiario."
            )

    async def _validate_batch_not_completed(self, batch_id: UUID, action: str) -> None:
        if self.batch_status_validator and await self.batch_status_validator.is_batch_completed(batch_id):
            raise ConflictException(
                f"El lote al que pertenece este expediente ya fue procesado y cerrado, no admite más {action}."
            )
