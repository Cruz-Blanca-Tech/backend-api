import sys
import unittest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

sys.path.insert(0, ".")

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.domain.shared.rules.dossier_status_validator import DossierStatusValidator
from src.contexts.data_quality_triage.domain.shared.ports.batch_status_validator import BatchStatusValidatorPort
from src.core.validators.exceptions import ConflictException


class TestDossierStatusValidator(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.batch_id = uuid4()
        self.case_id = uuid4()
        self.mock_batch_validator = AsyncMock(spec=BatchStatusValidatorPort)
        self.validator = DossierStatusValidator(batch_status_validator=self.mock_batch_validator)

    def _create_case(self, status: TriageStatus, verdict: TriageVerdict = TriageVerdict.REQUIRES_TRIAGE) -> TriageCase:
        return TriageCase(
            id=self.case_id,
            batch_id=self.batch_id,
            activity_type="EDUCA_INSCRIPTION",
            dni_reference="12345678",
            dossier_data={"beneficiary": {"dni": "12345678"}},
            document_ids={},
            confidence_scores={},
            status=status,
            verdict=verdict,
            discrepancies=[],
        )

    # ── Test de corrección ──────────────────────────────────────────

    async def test_correction_blocked_when_batch_is_completed(self):
        self.mock_batch_validator.is_batch_completed.return_value = True
        case = self._create_case(TriageStatus.PENDING_REVIEW)

        with self.assertRaises(ConflictException) as ctx:
            await self.validator.validate_can_be_corrected(case)
        self.assertIn("cerrado", ctx.exception.message)
        self.assertIn("correcciones", ctx.exception.message)

    async def test_correction_allowed_when_batch_open_and_case_approved(self):
        self.mock_batch_validator.is_batch_completed.return_value = False
        case = self._create_case(TriageStatus.APPROVED, TriageVerdict.AUTO_APPROVED)

        # No debe lanzar excepción: un caso aprobado puede corregirse mientras el lote no esté cerrado
        await self.validator.validate_can_be_corrected(case)

    async def test_correction_blocked_when_case_is_rejected(self):
        self.mock_batch_validator.is_batch_completed.return_value = False
        case = self._create_case(TriageStatus.REJECTED)

        with self.assertRaises(ConflictException) as ctx:
            await self.validator.validate_can_be_corrected(case)
        self.assertIn("rechazado", ctx.exception.message)
        self.assertIn("correcciones", ctx.exception.message)

    async def test_correction_allowed_when_batch_open_and_case_pending(self):
        self.mock_batch_validator.is_batch_completed.return_value = False
        case = self._create_case(TriageStatus.PENDING_REVIEW)

        # No debe lanzar excepción
        await self.validator.validate_can_be_corrected(case)

    # ── Test de rechazo ─────────────────────────────────────────────

    async def test_rejection_blocked_when_batch_is_completed(self):
        self.mock_batch_validator.is_batch_completed.return_value = True
        case = self._create_case(TriageStatus.PENDING_REVIEW)

        with self.assertRaises(ConflictException) as ctx:
            await self.validator.validate_can_be_rejected(case)
        self.assertIn("cerrado", ctx.exception.message)
        self.assertIn("rechazos", ctx.exception.message)

    async def test_rejection_allowed_when_batch_open_and_case_approved(self):
        self.mock_batch_validator.is_batch_completed.return_value = False
        case = self._create_case(TriageStatus.APPROVED, TriageVerdict.AUTO_APPROVED)

        # No debe lanzar excepción: un caso aprobado puede rechazarse mientras el lote no esté cerrado
        await self.validator.validate_can_be_rejected(case)

    async def test_rejection_blocked_when_case_is_already_rejected(self):
        self.mock_batch_validator.is_batch_completed.return_value = False
        case = self._create_case(TriageStatus.REJECTED)

        with self.assertRaises(ConflictException) as ctx:
            await self.validator.validate_can_be_rejected(case)
        self.assertIn("rechazado", ctx.exception.message)
        self.assertIn("rechazos", ctx.exception.message)

    async def test_rejection_allowed_when_batch_open_and_case_pending(self):
        self.mock_batch_validator.is_batch_completed.return_value = False
        case = self._create_case(TriageStatus.PENDING_REVIEW)

        # No debe lanzar excepción
        await self.validator.validate_can_be_rejected(case)


if __name__ == "__main__":
    unittest.main()
