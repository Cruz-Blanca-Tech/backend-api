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
        Lanza ConflictException si el lote al que pertenece ya fue cerrado o si el
        expediente ya se encuentra finalizado (aprobado o rechazado).
        """
        await self._validate_batch_not_completed(case.batch_id, action="correcciones")
        self._validate_case_not_finalized(case, action="correcciones")

    async def validate_can_be_rejected(self, case: TriageCase) -> None:
        """
        Valida que el expediente pueda ser rechazado.
        Lanza ConflictException si el lote al que pertenece ya fue cerrado o si el
        expediente ya se encuentra finalizado (aprobado o rechazado).
        """
        await self._validate_batch_not_completed(case.batch_id, action="rechazos")
        self._validate_case_not_finalized(case, action="rechazos")

    async def _validate_batch_not_completed(self, batch_id: UUID, action: str) -> None:
        if self.batch_status_validator and await self.batch_status_validator.is_batch_completed(batch_id):
            raise ConflictException(
                f"El lote al que pertenece este expediente ya fue procesado y cerrado, no admite más {action}."
            )

    def _validate_case_not_finalized(self, case: TriageCase, action: str) -> None:
        if case.status == TriageStatus.APPROVED:
            raise ConflictException(
                f"El expediente ya se encuentra aprobado y no admite más {action}."
            )
        if case.status == TriageStatus.REJECTED:
            raise ConflictException(
                f"El expediente ya se encuentra rechazado y no admite más {action}."
            )
