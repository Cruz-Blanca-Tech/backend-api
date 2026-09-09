import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from src.contexts.document_intake_ocr.application.use_cases.process_batch.process_batch import ProcessBatchUseCase
from src.contexts.document_intake_ocr.application.schemas.batch_schema import ProcessBatchRequest
from src.contexts.document_intake_ocr.application.schemas.file_item_schema import FileItemSchema
from src.contexts.document_intake_ocr.domain.entities.activity import Activity
from src.contexts.document_intake_ocr.domain.value_objects.activity_requirement import ActivityRequirement
from src.contexts.document_intake_ocr.domain.entities.document_type import DocumentTypeConfig
from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode
from src.core.validators.exceptions import DomainValidationError

@pytest.mark.asyncio
async def test_process_batch_raises_when_no_valid_files():
    activity_id = uuid4()
    doc_config = DocumentTypeConfig(
        id=uuid4(),
        name="Ficha",
        code=DocumentTypeCode("FINS"),
        year=2026,
        model_id="model-fins",
        version=1,
        preview_image_url="http://example.com/fins.png"
    )
    req = ActivityRequirement(
        document_config=doc_config,
        is_required=True,
        confidence_threshold=0.85
    )
    activity = Activity(
        id=activity_id,
        name="INSCRIPCIÓN A EDUCA 2026 - I",
        program_id=uuid4(),
        required_documents=[req],
        is_active=True
    )

    activity_repo = AsyncMock()
    activity_repo.get_by_id.return_value = activity
    batch_repo = AsyncMock()
    orchestrator = MagicMock()

    use_case = ProcessBatchUseCase(
        activity_repo=activity_repo,
        batch_repo=batch_repo,
        batch_orchestrator=orchestrator
    )

    # Request with an invalid document code (e.g. DNIPAPA)
    request = ProcessBatchRequest(
        activity_id=activity_id,
        files=[FileItemSchema(source_id="drive_1", file_name="91796223_DNIPAPA.jpg")],
        description="Test batch"
    )

    background_tasks = MagicMock()

    with pytest.raises(DomainValidationError) as exc_info:
        await use_case.execute(
            request=request,
            user_id=uuid4(),
            user_email="test@cruz-blanca.org",
            background_tasks=background_tasks
        )

    assert "Ninguno de los archivos cumple con la nomenclatura" in str(exc_info.value)
    batch_repo.save.assert_not_called()
    background_tasks.add_task.assert_not_called()


@pytest.mark.asyncio
async def test_append_documents_to_dossier():
    from src.contexts.document_intake_ocr.application.use_cases.append_documents_use_case import AppendDocumentsUseCase
    from src.contexts.document_intake_ocr.application.schemas.batch_schema import AppendDocumentsRequest
    from src.contexts.document_intake_ocr.domain.entities.extraction_batch import ExtractionBatch
    from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
    from src.contexts.document_intake_ocr.domain.value_objects.dni import DNI

    activity_id = uuid4()
    doc_config = DocumentTypeConfig(
        id=uuid4(),
        name="Ficha",
        code=DocumentTypeCode("FINS"),
        year=2026,
        model_id="model-fins",
        version=1,
        preview_image_url="http://example.com/fins.png"
    )
    req = ActivityRequirement(
        document_config=doc_config,
        is_required=True,
        confidence_threshold=0.85
    )
    activity = Activity(
        id=activity_id,
        name="INSCRIPCIÓN A EDUCA 2026 - I",
        program_id=uuid4(),
        required_documents=[req],
        is_active=True
    )

    batch_id = uuid4()
    user_id = uuid4()
    batch = ExtractionBatch(
        id=batch_id,
        activity_id=activity_id,
        created_by=user_id,
        description="Lote de prueba"
    )

    activity_repo = AsyncMock()
    activity_repo.get_by_id.return_value = activity
    batch_repo = AsyncMock()
    batch_repo.get_by_id.return_value = batch

    storage_adapter = MagicMock()
    single_doc_processor = MagicMock()
    event_publisher = MagicMock()

    use_case = AppendDocumentsUseCase(
        activity_repo=activity_repo,
        batch_repo=batch_repo,
        storage_adapter=storage_adapter,
        single_doc_processor=single_doc_processor,
        event_publisher=event_publisher
    )

    request = AppendDocumentsRequest(
        files=[FileItemSchema(source_id="drive_fins", file_name="91796223_FINS.jpg")]
    )

    background_tasks = MagicMock()

    response = await use_case.execute(
        batch_id=batch_id,
        dni_reference="91796223",
        request=request,
        user_id=user_id,
        user_email="test@cruz-blanca.org",
        background_tasks=background_tasks
    )

    assert response.batch_id == batch_id
    assert response.dni_reference == "91796223"
    assert response.added_documents_count == 1
    assert response.rejected_documents_count == 0
    assert response.dossier_status == "COMPLETE"
    batch_repo.save.assert_called_once()
    background_tasks.add_task.assert_called_once()

