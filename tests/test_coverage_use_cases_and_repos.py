from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest

from src.contexts.document_intake_ocr.application.use_cases.reprocess_dossier_use_case import (
    ReprocessDossierUseCase,
)
from src.contexts.document_intake_ocr.domain.entities.document import (
    DocumentItem,
    DocumentStatus,
)
from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
from src.contexts.document_intake_ocr.domain.value_objects.document_code import (
    DocumentTypeCode,
)
from src.contexts.document_intake_ocr.domain.value_objects.group_key import GroupKey
from src.contexts.data_quality_triage.application.use_cases.retry_case_sync_use_case import (
    RetryCaseSyncUseCase,
)
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import (
    TriageStatus,
)
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_analytics_repository import (
    SqlAnalyticsRepository,
)
from src.contexts.document_intake_ocr.application.use_cases.list_batches_use_case import (
    ListBatchesUseCase,
)
from src.contexts.document_intake_ocr.application.schemas.batch_schema import (
    ListBatchesRequest,
)
from src.contexts.core_beneficiary_management.application.event_handlers.mdm_event_handlers import (
    handle_mdm_dossier_approved,
    handle_mdm_pdf_generated,
)
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.shared.events.dossier_pdf_generated_event import (
    DossierPdfGeneratedEvent,
)
from src.contexts.data_quality_triage.application.shared.use_cases.reject_batch_use_case import (
    RejectBatchUseCase,
)
from src.contexts.reporting_analytics.features.operations.application.use_cases.export_ocr_audit_use_case import (
    ExportOcrAuditUseCase,
)
from src.contexts.reporting_analytics.features.operations.infrastructure.repositories.sql_operations_repository import (
    SqlOperationsRepository,
)
from src.contexts.data_quality_triage.application.shared.handlers.triage_event_handler import (
    TriageEventHandler,
    handle_batch_ocr_completed,
    handle_documents_extracted,
)
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent
from src.contexts.shared.events.batch_ocr_completed_event import BatchOcrCompletedEvent
from src.core.validators.exceptions import EntityNotFoundException


def _make_session_cm(mock_session):
    @asynccontextmanager
    async def _cm():
        yield mock_session

    return _cm


# ---------------------------------------------------------------------------
# 1. ReprocessDossierUseCase
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reprocess_dossier_use_case_flows():
    batch_repo = MagicMock()
    activity_repo = MagicMock()
    storage = MagicMock()
    single_proc = MagicMock()
    publisher = MagicMock()

    uc = ReprocessDossierUseCase(batch_repo, activity_repo, storage, single_proc, publisher)
    b_id = uuid4()

    # 1. Batch no encontrado
    batch_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(EntityNotFoundException):
        await uc.execute(b_id, "70000001", "u@cruz-blanca.org", MagicMock())

    # 2. Actividad no encontrada
    doc_failed = DocumentItem(
        id=uuid4(),
        source_id="s1",
        file_name="70000001_FINS.jpg",
        dni_reference=GroupKey("70000001"),
        document_code=DocumentTypeCode("FINS"),
        status=DocumentStatus.FAILED,
    )
    fake_batch = SimpleNamespace(
        id=b_id,
        activity_id=uuid4(),
        dossiers=[],
        rejected_documents=[doc_failed],
        _rejected_documents=[doc_failed],
        status=SimpleNamespace(value="FAILED"),
        add_dossier=lambda d: fake_batch.dossiers.append(d),
        get_all_documents=lambda: [doc_failed],
        mark_as_completed=MagicMock(),
    )
    batch_repo.get_by_id = AsyncMock(return_value=fake_batch)
    activity_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(EntityNotFoundException):
        await uc.execute(b_id, "70000001", "u@cruz-blanca.org", MagicMock())

    # 3. Expediente no encontrado
    fake_activity = SimpleNamespace(
        id=fake_batch.activity_id,
        name="EDUCA",
        required_documents=[],
        get_model_id_for_document=lambda code: "model-v1",
    )
    activity_repo.get_by_id = AsyncMock(return_value=fake_activity)
    with pytest.raises(EntityNotFoundException):
        await uc.execute(b_id, "99999999", "u@cruz-blanca.org", MagicMock())

    # 4. Flujo exitoso recreando dossier desde documentos rechazados
    batch_repo.save = AsyncMock()
    storage.ensure_batch_directory = AsyncMock(return_value="folder_1")

    async def _proc_ok(doc, **kwargs):
        doc.status = DocumentStatus.READY_FOR_REVIEW

    single_proc.execute = AsyncMock(side_effect=_proc_ok)
    publisher.publish_created = AsyncMock()

    res = await uc.execute(b_id, "70000001", "u@cruz-blanca.org", MagicMock())
    assert "reprocesado" in res["message"]
    publisher.publish_created.assert_called_once()

    # 5. Flujo donde single_doc_processor lanza excepción
    single_proc.execute = AsyncMock(side_effect=RuntimeError("OCR error"))
    res_err = await uc.execute(b_id, "70000001", "u@cruz-blanca.org", MagicMock())
    assert "reprocesado" in res_err["message"]

    # 6. _process_in_background
    mock_session = MagicMock()
    with patch(
        "src.core.database.async_session_maker",
        new=_make_session_cm(mock_session),
    ), patch(
        "src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_batch_repository.SqlBatchRepository"
    ) as mock_bg_b, patch(
        "src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_activity_repository.SqlActivityRepository"
    ) as mock_bg_a:
        doc_failed.status = DocumentStatus.PENDING
        mock_bg_b.return_value.get_by_id = AsyncMock(return_value=fake_batch)
        mock_bg_b.return_value.save = AsyncMock()
        mock_bg_a.return_value.get_by_id = AsyncMock(return_value=fake_activity)
        single_proc.execute = AsyncMock(side_effect=_proc_ok)
        publisher.publish_batch_ocr_completed = AsyncMock()
        await uc._process_in_background(b_id, "70000001", "u@cruz-blanca.org")
        await uc._process_in_background(b_id, "NO_EXISTE", "u@cruz-blanca.org")


# ---------------------------------------------------------------------------
# 2. RetryCaseSyncUseCase
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retry_case_sync_use_case():
    repo = MagicMock()
    uc = RetryCaseSyncUseCase(repo)
    c_id = uuid4()

    # No existe
    repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(ValueError):
        await uc.execute(c_id)

    # No está APPROVED
    repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(status=TriageStatus.PENDING_REVIEW)
    )
    with pytest.raises(ValueError):
        await uc.execute(c_id)

    # Ya está SYNCED
    repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(
            status=TriageStatus.APPROVED,
            sync_status="SYNCED",
            dni_reference="70000001",
        )
    )
    with pytest.raises(ValueError):
        await uc.execute(c_id)

    # Sincronización exitosa -> FINALIZED y SYNC_FAILED
    pending_case = SimpleNamespace(
        id=c_id,
        batch_id=uuid4(),
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="70000001",
        dossier_data={"beneficiary": {"dni": "70000001"}},
        resolved_by=uuid4(),
        status=TriageStatus.APPROVED,
        sync_status="FAILED",
    )
    repo.get_by_id = AsyncMock(return_value=pending_case)

    mock_session = MagicMock()
    mock_session.commit = AsyncMock()

    with patch(
        "src.contexts.data_quality_triage.application.use_cases.retry_case_sync_use_case.handle_mdm_dossier_approved",
        new=AsyncMock(),
    ), patch(
        "src.contexts.data_quality_triage.application.use_cases.retry_case_sync_use_case.handle_dossier_approved",
        new=AsyncMock(),
    ), patch(
        "src.contexts.data_quality_triage.application.use_cases.retry_case_sync_use_case.async_session_maker",
        new=_make_session_cm(mock_session),
    ), patch(
        "src.contexts.data_quality_triage.application.use_cases.retry_case_sync_use_case.FinalizeBatchIfCompleteUseCase"
    ) as mock_fin:
        mock_fin.return_value.execute = AsyncMock(return_value="FINALIZED")
        out = await uc.execute(c_id)
        assert out["status"] == "SYNCED"
        assert "cerrado" in out["message"]

        mock_fin.return_value.execute = AsyncMock(return_value="SYNC_FAILED")
        out2 = await uc.execute(c_id)
        assert "sigue esperando" in out2["message"]

    # Error durante el handler
    with patch(
        "src.contexts.data_quality_triage.application.use_cases.retry_case_sync_use_case.handle_mdm_dossier_approved",
        new=AsyncMock(side_effect=RuntimeError("DB down")),
    ):
        with pytest.raises(ValueError):
            await uc.execute(c_id)


# ---------------------------------------------------------------------------
# 3. SqlAnalyticsRepository
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sql_analytics_repository():
    session = MagicMock()
    rows_summary = [
        SimpleNamespace(
            status="AUTO_APPROVED",
            confidence_scores={"a": 0.9, "b": 0.8},
        ),
        SimpleNamespace(
            status="CUSTOM_STATUS",
            confidence_scores={"a": 1.0},
        ),
    ]
    rows_issues = [
        SimpleNamespace(
            discrepancies=[
                {"field_name": "dni", "rule_description": "DNI invalido"},
                {"field_name": "dni", "rule_description": "DNI invalido"},
            ]
        ),
        SimpleNamespace(discrepancies=None),
    ]

    session.execute = AsyncMock(side_effect=[rows_summary, rows_issues])
    repo = SqlAnalyticsRepository(session)

    fake_status_enum = SimpleNamespace(
        AUTO_APPROVED=SimpleNamespace(value="AUTO_APPROVED"),
        PENDING_REVIEW=SimpleNamespace(value="PENDING_REVIEW"),
        MANUALLY_APPROVED=SimpleNamespace(value="MANUALLY_APPROVED"),
        MANUALLY_REJECTED=SimpleNamespace(value="MANUALLY_REJECTED"),
        REJECTED=SimpleNamespace(value="REJECTED"),
    )
    with patch(
        "src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_analytics_repository.TriageStatus",
        new=fake_status_enum,
    ):
        summary = await repo.get_summary_metrics()
        assert summary["total_cases"] == 2
        assert summary["status_counts"]["OTHER"] == 1
        assert summary["global_average_confidence"] > 0.8

    issues = await repo.get_top_issues(limit=5)
    assert len(issues) == 1
    assert issues[0]["count"] == 2


# ---------------------------------------------------------------------------
# 4. ListBatchesUseCase
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_batches_use_case():
    session = MagicMock()
    triage_service = MagicMock()
    triage_service.get_triage_summaries = AsyncMock(
        return_value={}
    )

    u_id = uuid4()
    b_id = uuid4()
    act_id = uuid4()
    prog_id = uuid4()

    doc_fail = SimpleNamespace(
        status=DocumentStatus.FAILED,
        file_name="bad.jpg",
        failure_reason="Ilegible",
    )
    doc_app = SimpleNamespace(
        status=DocumentStatus.APPROVED,
        file_name="ok.jpg",
        failure_reason=None,
    )
    fake_batch = SimpleNamespace(
        id=b_id,
        activity_id=act_id,
        created_by=u_id,
        status="COMPLETED",
        created_at=datetime.now(timezone.utc),
        documents=[doc_fail, doc_app],
        failure_reason=None,
        description="Lote 1",
        activity=SimpleNamespace(
            name="Inscripcion",
            program=SimpleNamespace(name="Educa"),
        ),
    )

    res_count = MagicMock()
    res_count.scalar.return_value = 1

    res_batches = MagicMock()
    res_batches.scalars.return_value.all.return_value = [fake_batch]

    res_users = MagicMock()
    res_users.scalars.return_value = [
        SimpleNamespace(id=u_id, full_name="Enzo Trujillo", email="enzo@cruz-blanca.org")
    ]

    session.execute = AsyncMock(side_effect=[res_count, res_batches, res_users])

    uc = ListBatchesUseCase(session, triage_service)
    req = ListBatchesRequest(
        activity_id=act_id,
        program_id=prog_id,
        status="COMPLETED",
        skip=0,
        limit=10,
    )
    resp = await uc.execute(req)
    assert resp.total == 1
    assert len(resp.batches) == 1
    assert resp.batches[0].created_by_name == "Enzo Trujillo"


# ---------------------------------------------------------------------------
# 5. MDM Event Handlers
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_mdm_event_handlers_success_and_failure():
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.add = MagicMock()

    event = DossierApprovedEvent(
        triage_case_id=uuid4(),
        batch_id=uuid4(),
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="70000001",
        dossier_data={},
        approved_by=uuid4(),
    )

    with patch(
        "src.contexts.core_beneficiary_management.application.event_handlers.mdm_event_handlers.async_session_maker",
        new=_make_session_cm(mock_session),
    ), patch(
        "src.contexts.core_beneficiary_management.application.event_handlers.mdm_event_handlers.ProcessApprovedTriageCaseUseCase"
    ) as mock_uc, patch(
        "src.contexts.core_beneficiary_management.application.event_handlers.mdm_event_handlers.DeadLetterService"
    ) as mock_dlq:
        mock_uc.return_value.execute = AsyncMock()
        mock_dlq.mark_resolved = AsyncMock()
        await handle_mdm_dossier_approved(event)
        mock_session.commit.assert_called()

        # Camino de fallo que registra en DeadLetter
        mock_uc.return_value.execute = AsyncMock(side_effect=RuntimeError("Sync fail"))
        mock_dlq.record_failure = AsyncMock()
        with pytest.raises(RuntimeError):
            await handle_mdm_dossier_approved(event)
        mock_dlq.record_failure.assert_called_once()

    # handle_mdm_pdf_generated (éxito y error)
    pdf_event = DossierPdfGeneratedEvent(
        batch_id=uuid4(),
        dni="70000001",
        document_type="CONSOLIDATED_DOSSIER",
        file_id="drive_file_1",
        year=2026,
    )
    with patch(
        "src.contexts.core_beneficiary_management.application.event_handlers.mdm_event_handlers.async_session_maker",
        new=_make_session_cm(mock_session),
    ), patch(
        "src.contexts.core_beneficiary_management.application.event_handlers.mdm_event_handlers.SaveHistoricalDocumentUseCase"
    ) as mock_pdf_uc:
        mock_pdf_uc.return_value.execute = AsyncMock()
        await handle_mdm_pdf_generated(pdf_event)

        mock_pdf_uc.return_value.execute = AsyncMock(side_effect=RuntimeError("PDF err"))
        await handle_mdm_pdf_generated(pdf_event)


# ---------------------------------------------------------------------------
# 6. RejectBatchUseCase
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reject_batch_use_case():
    triage_repo = MagicMock()
    session = MagicMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    validator = MagicMock()

    uc = RejectBatchUseCase(triage_repo, session, validator)
    b_id = uuid4()
    u_id = uuid4()

    # No rechazable
    validator.is_batch_rejectable = AsyncMock(return_value=False)
    with pytest.raises(ValueError):
        await uc.execute(b_id, u_id, "Motivo")

    # Sin casos
    validator.is_batch_rejectable = AsyncMock(return_value=True)
    triage_repo.get_all_by_batch_id = AsyncMock(return_value=[])
    with pytest.raises(EntityNotFoundException):
        await uc.execute(b_id, u_id, "Motivo")

    # Con casos (uno finalizado y otro abierto)
    c_open = SimpleNamespace(
        id=uuid4(),
        is_finalized=False,
        status=SimpleNamespace(value="PENDING_REVIEW"),
        document_ids={"FINS": uuid4()},
        reject=MagicMock(),
        pending_events=[SimpleNamespace()],
        clear_events=MagicMock(),
    )
    c_fin = SimpleNamespace(id=uuid4(), is_finalized=True, pending_events=[], clear_events=MagicMock())
    triage_repo.get_all_by_batch_id = AsyncMock(return_value=[c_open, c_fin])
    triage_repo.bulk_save = AsyncMock()

    with patch(
        "src.contexts.data_quality_triage.application.shared.use_cases.reject_batch_use_case.EventDispatcher.dispatch",
        new=AsyncMock(),
    ):
        count = await uc.execute(b_id, u_id, "Ilegible")
        assert count == 1
        c_open.reject.assert_called_once()


# ---------------------------------------------------------------------------
# 7. ExportOcrAuditUseCase & SqlOperationsRepository
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_export_ocr_audit_and_sql_operations_repo():
    session = MagicMock()
    mock_res = MagicMock()
    mock_res.mappings.return_value.all.return_value = [
        {
            "id": str(uuid4()),
            "batch_id": str(uuid4()),
            "dni_reference": "70000001",
            "status": "APPROVED",
            "verdict": "AUTO_APPROVED",
            "confidence_scores": {"dni": 0.99},
            "resolved_by": None,
            "resolved_at": None,
            "created_at": "2026-10-01 10:00:00",
        }
    ]
    session.execute = AsyncMock(return_value=mock_res)

    ops_repo = SqlOperationsRepository(session)
    assert len(await ops_repo.get_success_rate()) == 1
    assert len(await ops_repo.get_automation_level()) == 1
    assert len(await ops_repo.get_daily_volume()) == 1
    assert len(await ops_repo.get_rejected_cases_export()) == 1
    assert len(await ops_repo.get_ocr_audit_export()) == 1

    export_uc = ExportOcrAuditUseCase(ops_repo)
    chunks = [chunk async for chunk in export_uc.execute()]
    assert len(chunks) == 2
    assert "status_description" in chunks[0]
    assert "inscrito exitosamente" in chunks[1]


# ---------------------------------------------------------------------------
# 8. TriageEventHandler
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_triage_event_handlers():
    proc_uc = MagicMock()
    proc_uc.execute = AsyncMock()
    handler = TriageEventHandler(proc_uc)

    ev = DocumentsExtractedEvent(
        batch_id=uuid4(),
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="70000001",
    )
    await handler.handle(ev)
    proc_uc.execute.assert_called_once()

    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    with patch(
        "src.core.database.async_session_maker",
        new=_make_session_cm(mock_session),
    ), patch(
        "src.contexts.data_quality_triage.application.shared.handlers.triage_event_handler.ProcessDossierUseCase"
    ) as mock_p_cls:
        mock_p_cls.return_value.execute = AsyncMock()
        await handle_documents_extracted(ev)
        mock_session.commit.assert_called_once()

        batch_ev = BatchOcrCompletedEvent(batch_id=uuid4())
        await handle_batch_ocr_completed(batch_ev)
