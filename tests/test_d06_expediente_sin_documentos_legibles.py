"""D6: un expediente con todos sus documentos fallidos llega a triaje como INCOMPLETO."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contexts.data_quality_triage.application.shared.services.dossier_processor import (
    _all_documents_failed,
    _build_no_readable_documents_issue,
)
from src.contexts.document_intake_ocr.application.use_cases.process_batch.batch_processing_orchestrator import (
    BatchProcessingOrchestrator,
)
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import BatchStatus


def _doc(status, reason=None):
    return SimpleNamespace(status=status, failure_reason=reason)


def test_todos_fallidos():
    assert _all_documents_failed([_doc("FAILED"), _doc("failed")])


def test_mezcla_o_vacio_no_cuenta():
    assert not _all_documents_failed([_doc("FAILED"), _doc("READY_FOR_REVIEW")])
    assert not _all_documents_failed([])


def test_error_menciona_motivo():
    issue = _build_no_readable_documents_issue([_doc("FAILED", "Servicio no disponible: Azure")])
    assert issue.severity == "ERROR" and issue.field_name == "documents.ALL"
    assert "Ningun documento se pudo leer" in issue.rule_description
    assert "Azure" in issue.rule_description


def _orchestrator(batch):
    o = BatchProcessingOrchestrator.__new__(BatchProcessingOrchestrator)
    o.batch_repo = MagicMock(); o.batch_repo.get_by_id = AsyncMock(return_value=batch); o.batch_repo.save = AsyncMock()
    o.activity_repo = MagicMock(); o.activity_repo.get_by_id = AsyncMock(return_value=MagicMock())
    o.storage_adapter = MagicMock(); o.storage_adapter.ensure_batch_directory = AsyncMock(return_value="f")
    o.single_dossier_processor = MagicMock(); o.single_dossier_processor.execute = AsyncMock(return_value=0)
    o.event_publisher = MagicMock()
    o.event_publisher.publish_created = AsyncMock(); o.event_publisher.publish_batch_ocr_completed = AsyncMock()
    return o


def _batch(dossiers):
    b = MagicMock()
    b.id = "b1"; b.status = BatchStatus.PROCESSING; b.dossiers = dossiers
    docs = [d for ds in dossiers for d in ds.documents]
    b.get_all_documents.return_value = docs
    def done():
        b.status = BatchStatus.COMPLETED
    def fail(reason):
        b.status = BatchStatus.FAILED
    b.mark_as_completed.side_effect = done
    b.mark_as_failed.side_effect = fail
    return b


def _dossier(*statuses):
    return SimpleNamespace(dni_reference="1", documents=[SimpleNamespace(status=SimpleNamespace(value=s)) for s in statuses])


@pytest.mark.asyncio
async def test_expediente_todo_fallido_se_publica_si_el_lote_no_fallo_por_completo():
    ok, bad = _dossier("READY_FOR_REVIEW"), _dossier("FAILED", "FAILED")
    o = _orchestrator(_batch([ok, bad]))
    await o.run_pipeline("b1", "u@x")
    assert o.event_publisher.publish_created.await_count == 2


@pytest.mark.asyncio
async def test_si_todo_el_lote_fallo_no_se_publica_nada():
    o = _orchestrator(_batch([_dossier("FAILED"), _dossier("FAILED")]))
    await o.run_pipeline("b1", "u@x")
    o.event_publisher.publish_created.assert_not_called()
