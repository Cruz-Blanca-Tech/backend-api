import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import asyncio

from src.contexts.data_quality_triage.application.use_cases.verify_batch_completion_use_case import VerifyBatchCompletionUseCase
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import (
    TriageStatus, TriageVerdict, BatchVerificationStatus
)
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
import src.contexts.document_intake_ocr.infrastructure.persistence.model.program_model
import src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_model
import src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_requirement_model
import src.contexts.document_intake_ocr.infrastructure.persistence.model.document_type_config
import src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model
import src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model
import src.contexts.core_beneficiary_management.infrastructure.persistence.model

@pytest.mark.asyncio
async def test_verify_batch_completion_all_synced_success():
    batch_id = uuid4()
    mock_repo = MagicMock()
    mock_validator = MagicMock()
    mock_validator.is_batch_completed = AsyncMock(return_value=False)
    mock_validator.is_batch_ready_for_triage = AsyncMock(return_value=True)

    case1 = TriageCase(
        id=uuid4(), batch_id=batch_id, activity_type="EDUCA_INSCRIPTION", dni_reference="11111111",
        dossier_data={"beneficiary": {"dni": "11111111"}}, document_ids={}, confidence_scores={},
        status=TriageStatus.APPROVED, verdict=TriageVerdict.AUTO_APPROVED, discrepancies=[]
    )

    mock_repo.get_all_by_batch_id = AsyncMock(return_value=[case1])

    uc = VerifyBatchCompletionUseCase(mock_repo, mock_validator)

    with patch("src.contexts.data_quality_triage.application.use_cases.verify_batch_completion_use_case.handle_mdm_dossier_approved", new=AsyncMock()) as mock_mdm, \
         patch("src.contexts.data_quality_triage.application.use_cases.verify_batch_completion_use_case.handle_dossier_approved", new=AsyncMock()) as mock_ocr, \
         patch("src.contexts.data_quality_triage.application.use_cases.verify_batch_completion_use_case.async_session_maker") as mock_session_maker, \
         patch("src.core.events.event_dispatcher.EventDispatcher.dispatch_background") as mock_dispatch:
        
        mock_session = AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_session

        res = await uc.execute(batch_id)

        assert res["status"] == BatchVerificationStatus.COMPLETED
        assert mock_mdm.await_count == 1
        assert mock_ocr.await_count == 1
        assert mock_dispatch.called

@pytest.mark.asyncio
async def test_verify_batch_completion_auto_retry_and_sync_failed():
    batch_id = uuid4()
    mock_repo = MagicMock()
    mock_validator = MagicMock()
    mock_validator.is_batch_completed = AsyncMock(return_value=False)
    mock_validator.is_batch_ready_for_triage = AsyncMock(return_value=True)

    case1 = TriageCase(
        id=uuid4(), batch_id=batch_id, activity_type="EDUCA_INSCRIPTION", dni_reference="11111111",
        dossier_data={"beneficiary": {"dni": "11111111"}}, document_ids={}, confidence_scores={},
        status=TriageStatus.APPROVED, verdict=TriageVerdict.AUTO_APPROVED, discrepancies=[]
    )

    mock_repo.get_all_by_batch_id = AsyncMock(return_value=[case1])

    uc = VerifyBatchCompletionUseCase(mock_repo, mock_validator)

    # Simular que MDM falla en ambos intentos
    mock_mdm = AsyncMock(side_effect=Exception("Database lock error"))

    with patch("src.contexts.data_quality_triage.application.use_cases.verify_batch_completion_use_case.handle_mdm_dossier_approved", mock_mdm), \
         patch("src.contexts.data_quality_triage.application.use_cases.verify_batch_completion_use_case.handle_dossier_approved", new=AsyncMock()), \
         patch("src.contexts.data_quality_triage.application.use_cases.verify_batch_completion_use_case.async_session_maker") as mock_session_maker, \
         patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:

        mock_session = AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_session

        res = await uc.execute(batch_id)

        # Debe reintentar (2 intentos en total)
        assert mock_mdm.await_count == 2
        assert mock_sleep.await_count == 1
        # Debe retornar SYNC_FAILED
        assert res["status"] == BatchVerificationStatus.SYNC_FAILED
        assert res["failed_count"] == 1

@pytest.mark.asyncio
async def test_dead_letter_service_record_and_resolve():
    from src.contexts.shared.application.services.dead_letter_service import DeadLetterService
    from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent

    case_id = uuid4()
    event = DossierApprovedEvent(
        triage_case_id=case_id,
        batch_id=uuid4(),
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="12345678",
        dossier_data={"name": "test"},
        approved_by=uuid4()
    )

    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_res)

    # 1. Record failure
    fe = await DeadLetterService.record_failure(
        session=mock_session,
        event=event,
        handler_name="test_handler",
        error=Exception("Test error message"),
        aggregate_id=case_id
    )

    assert fe.event_name == "DossierApprovedEvent"
    assert fe.aggregate_id == case_id
    assert fe.error_message == "Test error message"
    assert mock_session.add.called

    # 2. Mark resolved
    mock_session.execute.return_value.rowcount = 1
    count = await DeadLetterService.mark_resolved(mock_session, case_id)
    assert count == 1

