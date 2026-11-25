import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest

from src.contexts.data_quality_triage.application.shared.services.llm_name_reconciler import (
    LLMDecision,
    LLMNameReconciler,
)
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import (
    FieldDiscrepancy,
)
from src.contexts.document_intake_ocr.infrastructure.adapters.google_drive_storage_adapter import (
    GoogleDriveStorageAdapter,
)
from src.contexts.document_intake_ocr.domain.value_objects.file_item import FileItem
from src.contexts.document_intake_ocr.infrastructure.adapters.llm_data_normalizer import (
    LLMDataNormalizer,
    _clean_ghosts_from_data,
    _is_ghost_text,
)
from src.contexts.document_intake_ocr.infrastructure.adapters.azure_document_extractor import (
    AzureDocumentExtractor,
)
from src.contexts.security_access.application.services.auth_service import AuthService
from src.contexts.document_intake_ocr.infrastructure.persistence.mappers.batch_mapper import (
    BatchMapper,
)
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import (
    BatchStatus,
    ExtractionBatch,
)
from src.contexts.document_intake_ocr.domain.entities.document import (
    DocumentItem,
    DocumentStatus,
)
from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode
from src.contexts.document_intake_ocr.domain.entities.dossier import Dossier
from src.contexts.document_intake_ocr.domain.value_objects.group_key import GroupKey
from src.core.validators.exceptions import ExternalServiceException


def _field(val):
    return SimpleNamespace(normalized_value=val, value=val)


# ---------------------------------------------------------------------------
# 1. LLMNameReconciler
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_llm_name_reconciler_full_flow_and_edge_cases():
    dniap = SimpleNamespace(
        document_number=_field("40000001"),
        first_name=_field("MARIA"),
        last_name=_field("RIVERA SOTO"),
    )
    dnibe = SimpleNamespace(
        document_number=_field("70000001"),
        first_name=_field("JUAN"),
        last_name=_field("CONDORI RIVERA"),
    )
    fins_adult = SimpleNamespace(
        role=SimpleNamespace(value="MOTHER"),
        dni=_field("40000001"),
        first_name=_field("MARIA"),
        last_name=_field("BIR"),
    )
    fins = SimpleNamespace(
        child_first_name=_field("JUAN"),
        child_last_name=_field("CONDORI RIVERA"),
        adults=[fins_adult],
    )
    dj = SimpleNamespace(
        child_dni=_field("70000001"),
        parents_father_dni=_field("40000002"),
        parents_father_name=_field("CARLOS CONDORI"),
        parents_mother_dni=_field("40000001"),
        parents_mother_name=_field("MARIA RIVERA"),
        guardian_dni=_field("40000001"),
    )
    dossier_adults = [
        SimpleNamespace(
            full_name=_field("MARIA BIR"),
            dni=_field("40000001"),
            relationship="MOTHER",
        ),
        SimpleNamespace(
            full_name=_field("CARLOS CONDORI"),
            dni=_field("40000002"),
            relationship="FATHER",
        ),
    ]

    llm_client = MagicMock()
    llm_client.chat.completions.create = AsyncMock()

    reconciler = LLMNameReconciler(
        llm_client=llm_client,
        deployment_name="gpt-4o-mini",
        dniap=dniap,
        fins=fins,
        dnibe=dnibe,
        dj=dj,
        dossier_adults=dossier_adults,
    )

    # 1. Lista vacía
    assert await reconciler.reconcile([]) == []

    # 2. Sin discrepancias de coherencia/apellido
    non_coherence = [
        FieldDiscrepancy(
            field_name="education.grade",
            expected_pattern="1RO",
            actual_value="2DO",
            rule_description="Grado distinto",
            severity="WARNING",
        )
    ]
    assert await reconciler.reconcile(non_coherence) == []

    # 3. Con discrepancia de coherencia exitosa + baja confianza + campo inválido
    issues = [
        FieldDiscrepancy(
            field_name="coherencia_apellidos",
            expected_pattern="RIVERA",
            actual_value="BIR",
            rule_description="Coherencia de apellido materno",
            severity="WARNING",
        )
    ]

    llm_payload = {
        "decisions": [
            {
                "person": "mother",
                "field": "paternal_surname",
                "chosen_value": "RIVERA",
                "confidence": 0.95,
                "reasoning": "Error OCR vocálico",
            },
            {
                "person": "father",
                "field": "first_name",
                "chosen_value": "CARLOS",
                "confidence": 0.90,
                "reasoning": "Nombre padre",
            },
            {
                "person": "mother",
                "field": "maternal_surname",
                "chosen_value": "SOTO",
                "confidence": 0.85,
                "reasoning": "Segundo apellido madre",
            },
            {
                "person": "mother",
                "field": "paternal_surname",
                "chosen_value": "BAJA",
                "confidence": 0.50,
                "reasoning": "Confianza baja",
            },
            {
                "person": "mother",
                "field": "invalid_field",
                "chosen_value": "X",
                "confidence": 0.95,
                "reasoning": "Campo inválido",
            },
            {
                "person": "unknown_person",
                "field": "first_name",
                "chosen_value": "X",
                "confidence": 0.95,
                "reasoning": "Persona no mapeada",
            },
            {
                "person": "",
                "field": "first_name",
                "chosen_value": "",
                "confidence": 0.95,
            },
        ],
        "unresolved": [{"person": "father", "field": "maternal_surname", "reason": "Ambiguo"}],
    }
    mock_resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(llm_payload)))]
    )
    llm_client.chat.completions.create.return_value = mock_resp

    res = await reconciler.reconcile(issues)
    assert len(res) == 3
    assert res[0].expected_pattern == "RIVERA"
    assert res[0].severity == "INFO"

    # 4. Respuesta vacía del LLM
    llm_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=""))]
    )
    assert await reconciler.reconcile(issues) == []

    # 5. JSON inválido del LLM
    llm_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="{invalid-json"))]
    )
    assert await reconciler.reconcile(issues) == []

    # 6. Excepción de red en LLM y formato sin adultos/DJ
    reconciler_empty = LLMNameReconciler(
        llm_client=llm_client,
        deployment_name="gpt-4o-mini",
        dniap=dniap,
        fins=SimpleNamespace(child_first_name=None, child_last_name=None, adults=[]),
        dnibe=dnibe,
        dj=None,
        dossier_adults=[],
    )
    llm_client.chat.completions.create.side_effect = RuntimeError("Timeout")
    assert await reconciler_empty.reconcile(issues) == []
    assert reconciler_empty._format_dj({}) == "  (sin DJ)"

    dec = LLMDecision("mother", "first_name", "MARIA", 0.9, "ok")
    assert dec.person == "mother"


# ---------------------------------------------------------------------------
# 2. GoogleDriveStorageAdapter
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_google_drive_storage_adapter_methods():
    creds_info = {"client_email": "robot@cruz-blanca.org"}
    adapter = GoogleDriveStorageAdapter(creds_info, ["scope1"], "base_folder_123")
    file_item = FileItem(file_id="f1", file_name="doc.jpg")
    png_item = FileItem(file_id="f2", file_name="doc.png")

    mock_service = MagicMock()
    # list().execute() -> primero vacío (crea carpeta), luego con archivos (actualiza)
    mock_service.files().list().execute.side_effect = [
        {"files": []},
        {"files": [{"id": "existing_act"}]},
        {"files": []},
        {"files": [{"id": "existing_file"}]},
        {"files": [{"id": "existing_ben"}]},
        {"files": []},
    ]
    mock_service.files().create().execute.return_value = {"id": "created_id"}
    mock_service.files().update().execute.return_value = {"id": "updated_id"}
    mock_service.files().get_media().execute.return_value = b"PDF_BYTES"

    with patch(
        "src.contexts.document_intake_ocr.infrastructure.adapters.google_drive_storage_adapter.service_account.Credentials.from_service_account_info"
    ) as mock_creds, patch(
        "src.contexts.document_intake_ocr.infrastructure.adapters.google_drive_storage_adapter.build",
        return_value=mock_service,
    ):
        mock_creds.return_value.with_subject.return_value = MagicMock()

        # ensure_batch_directory (crea carpeta de actividad y luego la encuentra)
        folder1 = await adapter.ensure_batch_directory("EDUCA", "b1")
        assert folder1 == "created_id"
        folder2 = await adapter.ensure_batch_directory("EDUCA", "b2")
        assert folder2 == "created_id"

        # copy_to_custody (jpg y png -> create y update)
        link1 = await adapter.copy_to_custody(file_item, "target_f", "user@cruz-blanca.org")
        assert link1 == "created_id"
        link2 = await adapter.copy_to_custody(png_item, "target_f", "user@cruz-blanca.org")
        assert link2 == "updated_id"

        # download_file
        data = await adapter.download_file(file_item, "user@cruz-blanca.org")
        assert data == b"PDF_BYTES"

        # ensure_beneficiary_directory (existente y nuevo)
        ben1 = await adapter.ensure_beneficiary_directory("70000001")
        assert ben1 == "existing_ben"
        ben2 = await adapter.ensure_beneficiary_directory("70000002")
        assert ben2 == "created_id"

        # download_file_to_memory con URL y con ID directo
        mem1 = adapter.download_file_to_memory("https://drive.google.com/file/d/ABC_123/view")
        assert mem1 == b"PDF_BYTES"
        with pytest.raises(ValueError):
            adapter.download_file_to_memory("https://drive.google.com/invalid_url")

    # Manejo de errores envueltos en ExternalServiceException
    with patch.object(adapter, "_sync_ensure_batch_directory", side_effect=RuntimeError("boom")):
        with pytest.raises(ExternalServiceException):
            await adapter.ensure_batch_directory("ACT", "b1")

    with patch.object(adapter, "_sync_copy_to_custody", side_effect=RuntimeError("boom")):
        with pytest.raises(ExternalServiceException):
            await adapter.copy_to_custody(file_item, "f", "u@cruz-blanca.org")

    with patch.object(adapter, "_sync_download_file", side_effect=RuntimeError("boom")):
        with pytest.raises(ExternalServiceException):
            await adapter.download_file(file_item, "u@cruz-blanca.org")


# ---------------------------------------------------------------------------
# 3. LLMDataNormalizer
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_llm_data_normalizer_and_ghost_cleaner():
    assert _is_ghost_text("08TONA 80") is True
    assert _is_ghost_text("EVEN") is True
    assert _is_ghost_text("JUAN PEREZ") is False
    assert _is_ghost_text(None) is False

    dirty = {
        "child": "08TONA 80",
        "valid": "MARIA",
        "tags": ["EVEN", "VALID_TAG"],
        "adults": [
            {"full_name": "08TONA", "dni": "123"},
            {"full_name": "CARLOS PEREZ", "dni": "12345678"},
        ],
    }
    cleaned = _clean_ghosts_from_data(dirty)
    assert cleaned["child"] is None
    assert cleaned["valid"] == "MARIA"
    assert cleaned["tags"] == ["VALID_TAG"]
    assert len(cleaned["adults"]) == 1
    assert _clean_ghosts_from_data("EVEN") is None

    with patch(
        "src.contexts.document_intake_ocr.infrastructure.adapters.llm_data_normalizer.AsyncAzureOpenAI"
    ) as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=json.dumps({"child_first_name": "JUAN", "ghost": "08TONA"})
                        )
                    )
                ]
            )
        )
        mock_openai_cls.return_value = mock_client

        normalizer = LLMDataNormalizer(api_key="k", endpoint="https://example.com")

        # Camino exitoso con fallo simulado de BD (usa fallback de colegios)
        with patch(
            "src.contexts.document_intake_ocr.infrastructure.adapters.llm_data_normalizer.async_session_maker",
            side_effect=RuntimeError("DB offline"),
        ):
            out = await normalizer.normalize(
                {"child_first_name": "J0an"},
                context={"dni_reference": "70000001", "document_code": "FINS"},
            )
            assert out["child_first_name"] == "JUAN"
            assert out["ghost"] is None

        # Camino de excepción del LLM (fallback limpio con warnings)
        mock_client.chat.completions.create.side_effect = RuntimeError("LLM error")
        with patch(
            "src.contexts.document_intake_ocr.infrastructure.adapters.llm_data_normalizer.async_session_maker",
            side_effect=RuntimeError("DB offline"),
        ):
            fallback = await normalizer.normalize({"name": "08TONA", "ok": "SI"})
            assert fallback["name"] is None
            assert fallback["ok"] == "SI"
            assert any("No se pudo normalizar" in w for w in fallback["warnings"])


# ---------------------------------------------------------------------------
# 4. AzureDocumentExtractor
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_azure_document_extractor_success_and_errors():
    with patch(
        "src.contexts.document_intake_ocr.infrastructure.adapters.azure_document_extractor.DocumentAnalysisClient"
    ) as mock_cls:
        mock_client = MagicMock()
        mock_poller = MagicMock()
        mock_field = SimpleNamespace(value="70000001", confidence=0.98)
        mock_doc = SimpleNamespace(fields={"child_dni": mock_field})
        mock_poller.result = AsyncMock(return_value=SimpleNamespace(documents=[mock_doc]))
        mock_client.begin_analyze_document = AsyncMock(return_value=mock_poller)
        mock_client.close = AsyncMock()
        mock_cls.return_value = mock_client

        extractor = AzureDocumentExtractor("https://endpoint", "secret_key")
        res = await extractor.extract_data(b"bytes", "model-v1")
        assert res["confidence"] == 0.98
        assert res["fields"]["child_dni"]["value"] == "70000001"
        await extractor.close()

        # Error genérico
        mock_client.begin_analyze_document.side_effect = RuntimeError("Invalid image")
        with pytest.raises((ExternalServiceException, TypeError)):
            await extractor.extract_data(b"bad", "model-v1")


# ---------------------------------------------------------------------------
# 5. AuthService
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_auth_service_authenticate_refresh_and_logout():
    ext_auth = MagicMock()
    user_repo = MagicMock()
    refresh_repo = MagicMock()
    token_prov = MagicMock()
    policy = MagicMock()

    identity = SimpleNamespace(
        email="operador@cruz-blanca.org",
        full_name="Operador Uno",
        picture="https://img",
    )
    ext_auth.verify_token.return_value = identity

    token_pair = SimpleNamespace(access_token="acc_1", refresh_token="ref_1")
    token_prov.create_internal_token_pair = AsyncMock(return_value=token_pair)
    token_prov.hash_token.side_effect = lambda t: f"hash_{t}"

    service = AuthService(ext_auth, user_repo, refresh_repo, token_prov, policy)

    # 1. Usuario nuevo
    user_repo.get_by_email = AsyncMock(return_value=None)
    user_repo.save = AsyncMock()
    with patch(
        "src.contexts.security_access.application.services.auth_service.User"
    ) as mock_user_cls:
        new_user = SimpleNamespace(id=uuid4(), is_active=True, update_profile=MagicMock())
        mock_user_cls.create_new_user.return_value = new_user
        pair = await service.authenticate_user("google_jwt")
        assert pair.access_token == "acc_1"

    # 2. Usuario existente activo e inactivo
    active_user = SimpleNamespace(id=uuid4(), is_active=True, update_profile=MagicMock())
    user_repo.get_by_email = AsyncMock(return_value=active_user)
    pair2 = await service.authenticate_user("google_jwt")
    assert pair2.refresh_token == "ref_1"

    inactive_user = SimpleNamespace(id=uuid4(), is_active=False)
    user_repo.get_by_email = AsyncMock(return_value=inactive_user)
    with pytest.raises(PermissionError):
        await service.authenticate_user("google_jwt")

    # 3. Refresh session exitosa y fallida
    refresh_repo.get_session_by_token = AsyncMock(return_value=None)
    with pytest.raises(PermissionError):
        await service.refresh_user_session("old_tok")

    session_obj = SimpleNamespace(user_id=active_user.id, expires_at="2026-12-31")
    refresh_repo.get_session_by_token = AsyncMock(return_value=session_obj)
    user_repo.get_by_id = AsyncMock(return_value=active_user)
    refresh_repo.delete = AsyncMock()
    refresh_repo.save = AsyncMock()

    refreshed = await service.refresh_user_session("old_tok")
    assert refreshed.access_token == "acc_1"

    # 4. Logout
    await service.logout_user("ref_1")
    refresh_repo.delete.assert_called_with("hash_ref_1")


# ---------------------------------------------------------------------------
# 6. BatchMapper
# ---------------------------------------------------------------------------
def test_batch_mapper_to_model_and_to_domain():
    batch_id = uuid4()
    act_id = uuid4()
    user_id = uuid4()
    batch = ExtractionBatch(
        id=batch_id,
        activity_id=act_id,
        created_by=user_id,
        status=BatchStatus.COMPLETED,
        description="Lote de prueba",
    )
    dossier = Dossier(key=GroupKey("70000001"), activity_id=act_id, batch_id=batch_id)
    doc_ok = DocumentItem(
        id=uuid4(),
        source_id="f1",
        file_name="70000001_FINS.jpg",
        document_code=DocumentTypeCode("FINS"),
        dni_reference=GroupKey("70000001"),
        status=DocumentStatus.READY_FOR_REVIEW,
    )
    dossier.add_document(doc_ok)
    batch.add_dossier(dossier)

    doc_failed = DocumentItem(
        id=uuid4(),
        source_id="f2",
        file_name="bad.jpg",
        document_code=DocumentTypeCode("DJ"),
        dni_reference=GroupKey("70000002"),
        status=DocumentStatus.FAILED,
        failure_reason="Borroso",
    )
    batch.add_rejected_document(doc_failed)

    model = BatchMapper.to_model(batch)
    assert model.id == batch_id
    assert len(model.documents) == 2

    # Agregar un doc sin dni_reference para cubrir la rama de documento huérfano
    orphan_model = BatchMapper.to_model(batch).documents[0]
    orphan_model.dni_reference = None
    orphan_model.status = DocumentStatus.READY_FOR_REVIEW.value
    model.documents.append(orphan_model)

    reconstructed = BatchMapper.to_domain(model)
    assert len(reconstructed.dossiers) == 1
    assert len(reconstructed.rejected_documents) == 2
