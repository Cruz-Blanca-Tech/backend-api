from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest
from fastapi import HTTPException, Response

from src.contexts.shared.infrastructure.bus.event_bus import (
    InMemoryEventBus,
    get_event_bus,
)
from src.contexts.data_quality_triage.domain.educa.services.educa_inscription_policy import (
    EducaInscriptionPolicy,
)
from src.contexts.data_quality_triage.infrastructure.port.intake_document_provider import (
    IntakeDocumentProvider,
)
from src.contexts.document_intake_ocr.domain.value_objects.document_item.document_pipeline_state import (
    DocumentStatus as PipeStatus,
    PipelineState,
)
from src.contexts.data_quality_triage.application.use_cases.get_batches_summaries_use_case import (
    GetBatchesSummariesUseCase,
)
from src.contexts.document_intake_ocr.domain.value_objects.supported_mime_type import (
    SupportedMimeType,
)
from src.contexts.document_intake_ocr.infrastructure.dependencies import batch_deps
from src.contexts.data_quality_triage.infrastructure.dependencies import triage_deps
from src.contexts.core_beneficiary_management.presentation.api import beneficiary_router
from src.contexts.data_quality_triage.presentation.api.educa_router import (
    get_educa_triage_case,
    manual_triage_trigger,
    reject_triage_case,
    retry_case_sync,
    submit_correction,
)
from src.contexts.security_access.presentation.api.auth_router import (
    get_refresh_token,
    login,
    logout,
    refresh_token,
)
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import (
    SqlTriageRepository,
)
from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_activity_repository import (
    SqlActivityRepository,
)
from src.contexts.document_intake_ocr.application.event_handlers import (
    intake_event_handlers,
)
from src.contexts.data_quality_triage.application.use_cases import (
    retry_batch_sync_use_case,
)
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import (
    TriageStatus,
    TriageVerdict,
)
from src.contexts.security_access.domain.value_objects.role import Role
from src.core.validators.exceptions import ConflictException, DomainValidationError


def _make_session_cm(mock_session):
    @asynccontextmanager
    async def _cm():
        yield mock_session

    return _cm


# ---------------------------------------------------------------------------
# 1. Unimported domain & shared modules
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_unimported_domain_and_shared_modules():
    # InMemoryEventBus
    bus = get_event_bus()
    assert isinstance(bus, InMemoryEventBus)
    called = []

    async def _h(ev):
        called.append(ev)

    bus.subscribe(str, _h)
    await bus.publish("hello")
    assert called == ["hello"]

    # SupportedMimeType
    assert SupportedMimeType.PDF.extension == "pdf"
    assert SupportedMimeType.JPEG.extension == "jpg"
    assert SupportedMimeType.PNG.extension == "png"
    SupportedMimeType.validate("application/pdf")
    with pytest.raises(ValueError):
        SupportedMimeType.validate("text/plain")

    # PipelineState
    st = PipelineState.pending()
    assert st.status == PipeStatus.PENDING
    assert st.mark_processing().status == PipeStatus.PROCESSING_OCR
    assert st.mark_success().status == PipeStatus.READY_FOR_REVIEW
    assert st.mark_approved().status == PipeStatus.APPROVED

    # EducaInscriptionPolicy
    policy = EducaInscriptionPolicy()
    errs_ok = policy.evaluate(
        {
            "FINS": {"child_dni": "70000001"},
            "DJ": {"child_dni": "70000001"},
        }
    )
    assert errs_ok == []

    errs_mismatch = policy.evaluate(
        {
            "FINS": {"child_dni": "70000001"},
            "DJ": {"child_dni": "70000002"},
        }
    )
    assert any("Inconsistencia" in e for e in errs_mismatch)

    errs_missing = policy.evaluate({"FINS": {"child_first_name": "A"}, "DJ": {"child_name": "A"}})
    assert len(errs_missing) == 2

    # IntakeDocumentProvider
    session = MagicMock()
    doc_row = SimpleNamespace(
        id=uuid4(),
        code="FINS",
        file_name="70000001_FINS.jpg",
        extracted_data={"a": 1},
        confidence_score=0.95,
    )
    res_mock = MagicMock()
    res_mock.scalars.return_value.all.return_value = [doc_row]
    session.execute = AsyncMock(return_value=res_mock)
    provider = IntakeDocumentProvider(session)
    dtos = await provider.get_documents_by_batch_and_dni(uuid4(), "70000001")
    assert len(dtos) == 1
    assert dtos[0].document_code == "FINS"

    # GetBatchesSummariesUseCase
    triage_repo = MagicMock()
    b1 = uuid4()
    triage_repo.get_all_by_batch_ids = AsyncMock(
        return_value=[
            SimpleNamespace(batch_id=b1, verdict=TriageVerdict.AUTO_APPROVED),
            SimpleNamespace(batch_id=b1, verdict="CUSTOM_VERDICT"),
        ]
    )
    sum_uc = GetBatchesSummariesUseCase(triage_repo)
    assert await sum_uc.execute([]) == {}
    summaries = await sum_uc.execute([b1])
    assert summaries[b1]["total_cases"] == 2
    assert summaries[b1]["verdicts"]["CUSTOM_VERDICT"] == 1


# ---------------------------------------------------------------------------
# 2. Dependency providers (batch_deps & triage_deps)
# ---------------------------------------------------------------------------
def test_batch_and_triage_dependency_providers():
    fake_db = MagicMock()
    assert batch_deps.get_batch_repository(fake_db) is not None

    with patch.object(batch_deps.settings, "GOOGLE_CLIENT_SECRET", '{"client_email": "a@b.c"}'):
        st = batch_deps.get_storage_adapter()
        assert st is not None

    with patch(
        "src.contexts.document_intake_ocr.infrastructure.dependencies.batch_deps.AzureDocumentExtractor"
    ):
        ext = batch_deps.get_extractor_adapter()
        proc = batch_deps.get_single_document_processor(storage=MagicMock(), extractor=ext)
        d_proc = batch_deps.get_single_dossier_processor(doc_processor=proc)
        pub = batch_deps.get_dossier_event_publisher()
        orch = batch_deps.get_batch_orchestrator(
            activity_repo=MagicMock(),
            batch_repo=MagicMock(),
            storage=MagicMock(),
            dossier_processor=d_proc,
            event_publisher=pub,
        )
        assert batch_deps.get_process_batch_use_case(MagicMock(), MagicMock(), orch) is not None
        assert batch_deps.get_retry_batch_use_case(MagicMock(), orch) is not None
        assert batch_deps.get_documents_by_dossier_use_case(fake_db) is not None
        assert batch_deps.get_document_image_use_case(fake_db, MagicMock()) is not None
        assert batch_deps.get_list_batches_use_case(fake_db) is not None
        assert batch_deps.get_batches_summary_use_case(fake_db) is not None
        assert batch_deps.get_batch_by_id_use_case(fake_db) is not None
        assert (
            batch_deps.get_append_documents_use_case(
                MagicMock(), MagicMock(), MagicMock(), proc, pub
            )
            is not None
        )
        assert (
            batch_deps.get_reprocess_dossier_use_case(
                MagicMock(), MagicMock(), MagicMock(), proc, pub
            )
            is not None
        )

    # triage_deps
    t_repo = triage_deps.get_triage_repository(fake_db)
    d_repo = triage_deps.get_document_read_repository(fake_db)
    assert triage_deps.get_strategy_factory() is not None
    assert triage_deps.get_dossier_processor(fake_db, t_repo, d_repo, None) is not None
    val = triage_deps.get_dossier_status_validator(fake_db)
    assert triage_deps.get_submit_correction_use_case(fake_db, t_repo, val) is not None
    assert triage_deps.get_reject_batch_use_case(fake_db, t_repo) is not None
    assert triage_deps.get_reject_dossier_use_case(fake_db, t_repo, val) is not None
    assert triage_deps.get_cases_by_batch_use_case(t_repo) is not None
    assert triage_deps.get_verify_batch_completion_use_case(fake_db, t_repo) is not None
    assert triage_deps.get_batch_summary_use_case(t_repo) is not None
    assert triage_deps.get_retry_batch_sync_use_case(t_repo) is not None
    assert triage_deps.get_retry_case_sync_use_case(t_repo) is not None


# ---------------------------------------------------------------------------
# 3. Beneficiary Router, Educa Router & Auth Router
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_beneficiary_educa_and_auth_routers():
    # beneficiary_router
    db = MagicMock()
    adult_row = SimpleNamespace(
        id=uuid4(),
        dni="40000001",
        first_name="MARIA",
        last_name="LOPEZ",
        phone="999888777",
        role="MOTHER",
    )
    res_adults = MagicMock()
    res_adults.scalars.return_value.all.return_value = [adult_row]
    db.execute = AsyncMock(return_value=res_adults)
    found = await beneficiary_router.search_adult("MARIA", db=db)
    assert len(found) == 1

    from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import (
        BeneficiarySummaryResponse,
    )

    uc_list = MagicMock()
    item_summary = BeneficiarySummaryResponse(
        id=uuid4(),
        dni="70000001",
        first_name="JUAN",
        last_name="PEREZ",
        birth_date=None,
        age=8,
        gender="MALE",
        is_active=True,
        grade="2DO_PRIMARIA",
    )
    uc_list.execute = AsyncMock(return_value=SimpleNamespace(items=[item_summary], total=1))
    page = await beneficiary_router.get_beneficiaries(
        0, 10, use_case=uc_list, current_user=SimpleNamespace(role=Role.VISUALIZADOR)
    )
    assert page.total == 1

    uc_dni = MagicMock(execute=AsyncMock(return_value={"exists": False, "beneficiary": None}))
    assert (await beneficiary_router.get_beneficiary_by_dni("70000001", uc_dni))["exists"] is False

    uc_id = MagicMock(execute=AsyncMock(return_value=None))
    with pytest.raises(HTTPException) as exc:
        await beneficiary_router.get_beneficiary(uuid4(), uc_id)
    assert exc.value.status_code == 404

    uc_patch = MagicMock(execute=AsyncMock(side_effect=ValueError("No existe")))
    with pytest.raises(HTTPException) as exc2:
        await beneficiary_router.patch_beneficiary(uuid4(), MagicMock(), uc_patch)
    assert exc2.value.status_code == 404

    uc_create = MagicMock(execute=AsyncMock(side_effect=ConflictException("Duplicado")))
    with pytest.raises(HTTPException) as exc3:
        await beneficiary_router.create_beneficiary(MagicMock(), uc_create)
    assert exc3.value.status_code == 409

    uc_create.execute = AsyncMock(side_effect=DomainValidationError("Invalido"))
    with pytest.raises(HTTPException) as exc4:
        await beneficiary_router.create_beneficiary_with_id(uuid4(), MagicMock(), uc_create)
    assert exc4.value.status_code == 400

    # educa_router
    t_repo = MagicMock()
    t_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(HTTPException):
        await get_educa_triage_case(uuid4(), t_repo)

    t_repo.get_by_id = AsyncMock(return_value=SimpleNamespace(activity_type="OTHER"))
    with pytest.raises(HTTPException):
        await get_educa_triage_case(uuid4(), t_repo)
    with pytest.raises(HTTPException):
        await submit_correction(uuid4(), MagicMock(), MagicMock(), t_repo, MagicMock())
    with pytest.raises(HTTPException):
        await reject_triage_case(uuid4(), MagicMock(), MagicMock(), t_repo, MagicMock())

    t_repo.get_by_id = AsyncMock(return_value=SimpleNamespace(activity_type="EDUCA_INSCRIPTION"))
    rej_uc = MagicMock(execute=AsyncMock())
    rej_res = await reject_triage_case(
        uuid4(),
        SimpleNamespace(reason="Motivo valido"),
        rej_uc,
        t_repo,
        SimpleNamespace(user_id=uuid4()),
    )
    assert "rechazado" in rej_res["message"]

    retry_uc = MagicMock(execute=AsyncMock(side_effect=ValueError("Error sync")))
    with pytest.raises(HTTPException):
        await retry_case_sync(uuid4(), retry_uc)

    with patch("src.core.events.event_dispatcher.EventDispatcher.dispatch", new=AsyncMock()):
        trig = await manual_triage_trigger(uuid4(), "70000001")
        assert trig["status"] == "accepted"

    # auth_router
    resp = Response()
    auth_svc = MagicMock()
    auth_svc.authenticate_user = AsyncMock(
        return_value=SimpleNamespace(access_token="acc", refresh_token="ref")
    )
    login_out = await login(
        SimpleNamespace(google_token="gtok"), resp, auth_svc
    )
    assert login_out["access_token"] == "acc"

    auth_svc.authenticate_user = AsyncMock(side_effect=PermissionError("Dominio no permitido"))
    with pytest.raises(HTTPException) as e_forb:
        await login(SimpleNamespace(google_token="gtok"), resp, auth_svc)
    assert e_forb.value.status_code == 403

    with pytest.raises(HTTPException) as e_unauth:
        await refresh_token(resp, refresh_token=None, auth_service=auth_svc)
    assert e_unauth.value.status_code == 401

    auth_svc.refresh_user_session = AsyncMock(
        return_value=SimpleNamespace(access_token="acc2", refresh_token="ref2")
    )
    ref_out = await refresh_token(resp, refresh_token="old", auth_service=auth_svc)
    assert ref_out["access_token"] == "acc2"

    auth_svc.logout_user = AsyncMock()
    fake_req = SimpleNamespace(cookies={"refresh_token": "ref2"})
    assert await get_refresh_token(fake_req) == "ref2"
    logout_out = await logout(resp, fake_req, auth_svc)
    assert "cerrada" in logout_out["message"]


# ---------------------------------------------------------------------------
# 4. SqlTriageRepository & SqlActivityRepository
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sql_triage_and_activity_repositories():
    session = MagicMock()
    session.merge = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()

    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = None
    res_mock.scalar_one.return_value = 0
    res_mock.scalars.return_value.all.return_value = []
    res_mock.scalars.return_value.unique.return_value.all.return_value = []
    res_mock.fetchall.return_value = [("FINS", 0.85)]
    session.execute = AsyncMock(return_value=res_mock)

    t_repo = SqlTriageRepository(session)
    with patch(
        "src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository.TriageCaseMapper.to_model",
        return_value=MagicMock(),
    ):
        await t_repo.save(MagicMock())
        await t_repo.bulk_save([MagicMock()])

    assert await t_repo.get_by_id(uuid4()) is None
    assert await t_repo.get_by_dossier(uuid4(), "70000001") is None
    assert await t_repo.list_pending() == ([], 0)
    assert await t_repo.list_by_batch_id(uuid4()) == ([], 0)
    assert await t_repo.get_confidence_thresholds(uuid4()) == {"FINS": 0.85}
    assert await t_repo.get_all_by_batch_id(uuid4()) == []
    assert await t_repo.get_all_by_batch_ids([]) == []
    assert await t_repo.get_all_by_batch_ids([uuid4()]) == []

    a_repo = SqlActivityRepository(session)
    assert await a_repo.get_by_id(uuid4()) is None
    assert await a_repo.get_by_program_id(uuid4()) == []
    assert await a_repo.list_all_active() == []

    fake_act = SimpleNamespace(
        id=uuid4(),
        program_id=uuid4(),
        name="Educa",
        is_active=True,
        required_documents=[
            SimpleNamespace(
                document_config=SimpleNamespace(id=uuid4()),
                is_required=True,
                confidence_threshold=0.85,
            )
        ],
    )
    await a_repo.save(fake_act)
    session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 5. Intake Event Handlers & RetryBatchSyncUseCase
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_intake_event_handlers_and_retry_batch_sync():
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=SimpleNamespace(rowcount=2))
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    ev = SimpleNamespace(
        batch_id=uuid4(),
        dni_reference="70000001",
        reason="Error",
        document_ids=[uuid4()],
        approved_dossiers={"70000001": {"corrected_dni": "70000001", "documents": []}},
    )

    with patch.object(
        intake_event_handlers, "async_session_maker", new=_make_session_cm(mock_session)
    ), patch.object(
        intake_event_handlers, "GenerateBatchPdfsUseCase"
    ) as mock_pdf_uc:
        mock_pdf_uc.return_value.execute = AsyncMock()
        await intake_event_handlers.handle_dossier_approved(ev)
        await intake_event_handlers.handle_dossier_rejected(ev)
        await intake_event_handlers.handle_batch_rejected(ev)
        await intake_event_handlers.handle_batch_triage_completed(ev)

    # RetryBatchSyncUseCase
    t_repo = MagicMock()
    uc = retry_batch_sync_use_case.RetryBatchSyncUseCase(t_repo)
    b_id = uuid4()

    t_repo.get_all_by_batch_id = AsyncMock(return_value=[])
    res_nf = await uc.execute(b_id)
    assert res_nf["status"] == "NOT_FOUND"

    case_pending = SimpleNamespace(
        id=uuid4(),
        batch_id=b_id,
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="70000001",
        dossier_data={"beneficiary": {"dni": "70000001"}},
        document_ids={"FINS": uuid4()},
        resolved_by=uuid4(),
        status=TriageStatus.APPROVED,
        sync_status="FAILED",
    )
    t_repo.get_all_by_batch_id = AsyncMock(return_value=[case_pending])

    from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import (
        ExtractionBatchModel,
    )

    with patch.object(
        retry_batch_sync_use_case,
        "ExtractionBatchModel",
        new=ExtractionBatchModel,
        create=True,
    ), patch.object(
        retry_batch_sync_use_case,
        "async_session_maker",
        new=_make_session_cm(mock_session),
    ), patch.object(
        retry_batch_sync_use_case,
        "handle_mdm_dossier_approved",
        new=AsyncMock(),
    ), patch.object(
        retry_batch_sync_use_case,
        "handle_dossier_approved",
        new=AsyncMock(),
    ), patch.object(
        retry_batch_sync_use_case,
        "FinalizeBatchIfCompleteUseCase",
    ) as mock_fin, patch.object(
        retry_batch_sync_use_case.EventDispatcher,
        "dispatch_background",
    ):
        mock_fin.return_value.execute = AsyncMock(return_value="FINALIZED")
        res_ok = await uc.execute(b_id)
        assert res_ok["status"] == "FINALIZED"


@pytest.mark.asyncio
async def test_azure_adapter_duplicate_and_beneficiary_dto_mapper():
    import datetime
    from src.contexts.document_intake_ocr.infrastructure.adapters.azure_document_extractor_adapter import (
        AzureDocumentExtractor as AzureDupExtractor,
    )
    from src.contexts.core_beneficiary_management.presentation.mappers.beneficiary_dto_mapper import (
        BeneficiaryDtoMapper,
        calculate_age,
    )
    from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
    from src.contexts.core_beneficiary_management.domain.value_objects.gender import Gender

    assert calculate_age(None) is None
    assert calculate_age(datetime.date(2018, 1, 1)) >= 8

    assert BeneficiaryDtoMapper.to_response(None) is None
    assert BeneficiaryDtoMapper.to_mdm_snapshot(None) is None
    assert BeneficiaryDtoMapper.to_summary_response(None) is None

    fake_ben = SimpleNamespace(
        id=uuid4(),
        dni=DNI("70000001"),
        first_name="JUAN",
        last_name="PEREZ",
        birth_date=datetime.date(2018, 5, 10),
        gender=Gender.MALE,
        address="Ancon",
        religion_record=SimpleNamespace(baptized=True, first_communion=False),
        permissions_record=SimpleNamespace(haircut_permission=True, medical_exams_permission=True),
        enrollments=[SimpleNamespace(activity_code="ACT1")],
        medical_record=None,
        education_record=SimpleNamespace(
            id=uuid4(),
            beneficiary_id=uuid4(),
            school_name="SAN MARTIN",
            grade=SimpleNamespace(value="2DO_PRIMARIA"),
            knows_how_to_read=True,
            knows_how_to_write=True,
            has_repeated_grade=False,
            has_learning_difficulties=False,
        ),
        relatives=[
            SimpleNamespace(
                id=uuid4(),
                dni=DNI("40000001"),
                first_name="MARIA",
                last_name="LOPEZ",
                phone=SimpleNamespace(value="999888777"),
                role=SimpleNamespace(value="MOTHER"),
                is_guardian=True,
                is_emergency_contact=True,
            )
        ],
        historical_documents=[],
    )
    snap = BeneficiaryDtoMapper.to_mdm_snapshot(fake_ben)
    assert snap.dni == "70000001"
    assert len(snap.relatives) == 1

    summ = BeneficiaryDtoMapper.to_summary_response(fake_ben, active_activity_ids={"ACT1"})
    assert summ.is_active is True
    assert summ.grade == "2DO_PRIMARIA"

    with patch(
        "src.contexts.document_intake_ocr.infrastructure.adapters.azure_document_extractor_adapter.DocumentAnalysisClient"
    ) as mock_cls:
        mock_client = MagicMock()
        mock_poller = MagicMock()
        mock_poller.result = AsyncMock(
            return_value=SimpleNamespace(
                documents=[
                    SimpleNamespace(
                        fields={"dni": SimpleNamespace(value="70000001", confidence=0.95)}
                    )
                ]
            )
        )
        mock_client.begin_analyze_document = AsyncMock(return_value=mock_poller)
        mock_client.close = AsyncMock()
        mock_cls.return_value = mock_client

        dup = AzureDupExtractor("https://endpoint", "key")
        out = await dup.extract_data(b"123", "m1")
        assert out["confidence"] == 0.95
        await dup.close()


@pytest.mark.asyncio
async def test_remaining_unimported_and_demographics():
    from src.contexts.document_intake_ocr.application.event_publishers.activity_event_publisher import (
        ActivityEventPublisher,
    )
    from src.contexts.document_intake_ocr.application.event_publishers.document_type_config_event_publisher import (
        DocumentTypeConfigEventPublisher,
    )
    from src.contexts.data_quality_triage.domain.shared.entities.activity_policy import (
        ActivityPolicy,
    )
    from src.contexts.security_access.domain.exceptions.auth_errors import (
        InvalidCredentialsError,
        UserAlreadyExistsError,
        UserNotAuthorizedError,
    )
    from src.contexts.document_intake_ocr.domain.value_objects.sub_batch_validation_report import (
        SubBatchValidationReport,
    )
    from src.contexts.reporting_analytics.features.demographics.infrastructure.repositories.sql_demographics_repository import (
        SqlDemographicsRepository,
    )
    from src.contexts.reporting_analytics.features.demographics.application.use_cases.get_school_distribution_use_case import (
        GetSchoolDistributionUseCase,
    )

    bus = InMemoryEventBus()
    act_pub = ActivityEventPublisher(bus)
    with patch(
        "src.contexts.document_intake_ocr.application.event_publishers.activity_event_publisher.ActivityRequirementsConfiguredEvent",
        return_value=SimpleNamespace(),
    ):
        await act_pub.publish_created(
            SimpleNamespace(
                id=uuid4(),
                program_id=uuid4(),
                required_documents=[SimpleNamespace(code_str="FINS")],
            )
        )

    doc_pub = DocumentTypeConfigEventPublisher(bus)
    with patch(
        "src.contexts.document_intake_ocr.application.event_publishers.document_type_config_event_publisher.DocumentTypeConfigCreatedEvent",
        return_value=SimpleNamespace(),
    ):
        await doc_pub.publish_created(
            SimpleNamespace(id=uuid4(), name="Ficha", version="v1")
        )

    pol = ActivityPolicy(required_document_codes=["FINS", "DJ"])
    res_pol = pol.evaluate(SimpleNamespace(document_ids={"FINS": uuid4()}))
    assert res_pol.is_valid is False
    assert res_pol.missing_documents == ["DJ"]

    assert "registrado" in str(UserAlreadyExistsError("a@b.c"))
    assert "inválidas" in str(InvalidCredentialsError())
    assert "permisos" in str(UserNotAuthorizedError("a@b.c"))

    rep = SubBatchValidationReport(is_valid=False, missing_codes=[], extra_codes=[])
    assert rep.has_errors is True

    session = MagicMock()
    mock_res = MagicMock()
    mock_res.mappings.return_value.all.return_value = [
        {"school": "IE San Martin", "total": 10},
        {"school": "Villas de Ancon", "total": 5},
        {"school": "Colegio X", "total": 2},
    ]
    session.execute = AsyncMock(return_value=mock_res)

    dem_repo = SqlDemographicsRepository(session)
    assert len(await dem_repo.get_population_pyramid()) == 3
    assert len(await dem_repo.get_registration_growth()) == 3
    assert len(await dem_repo.get_document_coverage()) == 3
    assert len(await dem_repo.get_raw_school_distribution()) == 3
    assert len(await dem_repo.get_beneficiaries_master_export()) == 3

    dist_uc = GetSchoolDistributionUseCase(dem_repo)
    dist_resp = await dist_uc.execute()
    assert len(dist_resp.data) == 3


