"""D6: el reintento de lote vuelve a procesar los documentos FAILED."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contexts.document_intake_ocr.application.services.single_dossier_processor import SingleDossierProcessor
from src.contexts.document_intake_ocr.application.use_cases.process_batch.retry_batch_use_case import RetryBatchUseCase
from src.contexts.document_intake_ocr.domain.entities.document import DocumentStatus
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import BatchStatus
from src.core.validators.exceptions import DomainValidationError


def _processor():
    p = SingleDossierProcessor.__new__(SingleDossierProcessor)
    p.single_doc_processor = MagicMock()
    p.single_doc_processor.execute = AsyncMock()
    return p


def _dossier(status):
    doc = SimpleNamespace(status=status, failure_reason="boom", file_name="a.pdf", document_code="FINS")
    dossier = MagicMock()
    dossier.status = "COMPLETE"
    dossier.documents = [doc]
    return dossier, doc


def _activity():
    a = MagicMock()
    a.get_model_id_for_document.return_value = "model"
    a.required_documents = []
    return a


@pytest.mark.asyncio
async def test_sin_reintento_se_salta_el_fallido():
    p = _processor()
    dossier, doc = _dossier(DocumentStatus.FAILED)
    n = await p.execute(dossier, _activity(), "f", "u@x")
    assert n == 0
    p.single_doc_processor.execute.assert_not_called()


@pytest.mark.asyncio
async def test_con_reintento_se_procesa_el_fallido():
    p = _processor()
    dossier, doc = _dossier(DocumentStatus.FAILED)
    n = await p.execute(dossier, _activity(), "f", "u@x", retry_failed=True)
    assert n == 1
    p.single_doc_processor.execute.assert_awaited_once()
    assert doc.status == DocumentStatus.PENDING
    assert doc.failure_reason is None


def _retry(batch_status, doc_statuses):
    batch = MagicMock()
    batch.id = "b1"
    batch.status = batch_status
    batch.get_all_documents.return_value = [SimpleNamespace(status=s) for s in doc_statuses]
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=batch)
    repo.save = AsyncMock()
    orch = MagicMock()
    return RetryBatchUseCase(repo, orch), orch, batch


@pytest.mark.asyncio
async def test_lote_completed_con_fallidos_se_puede_reintentar():
    uc, orch, batch = _retry(BatchStatus.COMPLETED, [DocumentStatus.FAILED, DocumentStatus.READY_FOR_REVIEW])
    bg = MagicMock()
    await uc.execute("b1", "u@x", bg)
    bg.add_task.assert_called_once_with(orch.run_pipeline, "b1", "u@x", True)


@pytest.mark.asyncio
async def test_lote_completed_sin_fallidos_no_se_reintenta():
    uc, _, _ = _retry(BatchStatus.COMPLETED, [DocumentStatus.READY_FOR_REVIEW])
    with pytest.raises(DomainValidationError):
        await uc.execute("b1", "u@x", MagicMock())
