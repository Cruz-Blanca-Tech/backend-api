from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_db
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_document_read_repository import SqlDocumentReadRepository
from src.contexts.data_quality_triage.domain.shared.strategies.triage_strategy_factory import TriageStrategyFactory
from src.contexts.data_quality_triage.application.shared.services.dossier_processor import ProcessDossierUseCase
from src.contexts.data_quality_triage.application.shared.use_cases.submit_correction_use_case import SubmitCorrectionUseCase
from src.contexts.data_quality_triage.application.shared.use_cases.reject_batch_use_case import RejectBatchUseCase
from src.contexts.data_quality_triage.application.shared.use_cases.reject_dossier_use_case import RejectDossierUseCase
from src.contexts.data_quality_triage.application.shared.use_cases.get_cases_by_batch_use_case import GetCasesByBatchUseCase
from src.contexts.data_quality_triage.application.use_cases.verify_batch_completion_use_case import VerifyBatchCompletionUseCase
from src.contexts.data_quality_triage.application.use_cases.get_batch_summary_use_case import GetBatchSummaryUseCase

def get_triage_repository(session: AsyncSession = Depends(get_async_db)) -> SqlTriageRepository:
    return SqlTriageRepository(session=session)

def get_document_read_repository(session: AsyncSession = Depends(get_async_db)) -> SqlDocumentReadRepository:
    return SqlDocumentReadRepository(session=session)

def get_strategy_factory() -> TriageStrategyFactory:
    return TriageStrategyFactory()

def get_dossier_processor(session: AsyncSession = Depends(get_async_db), triage_repo: SqlTriageRepository = Depends(get_triage_repository), doc_repo: SqlDocumentReadRepository = Depends(get_document_read_repository)) -> ProcessDossierUseCase:
    return ProcessDossierUseCase(triage_repo=triage_repo, doc_repo=doc_repo, strategy_factory=TriageStrategyFactory(), session=session)

def get_submit_correction_use_case(session: AsyncSession = Depends(get_async_db), triage_repo: SqlTriageRepository = Depends(get_triage_repository)) -> SubmitCorrectionUseCase:
    return SubmitCorrectionUseCase(triage_repo=triage_repo, session=session)

def get_reject_batch_use_case(
    session: AsyncSession = Depends(get_async_db),
    triage_repo: SqlTriageRepository = Depends(get_triage_repository)
) -> RejectBatchUseCase:
    from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_batch_repository import SqlBatchRepository
    from src.contexts.data_quality_triage.infrastructure.adapters.batch_status_validator_adapter import BatchStatusValidatorAdapter

    batch_repo = SqlBatchRepository(session=session)
    validator = BatchStatusValidatorAdapter(batch_repository=batch_repo)
    return RejectBatchUseCase(triage_repo=triage_repo, session=session, batch_status_validator=validator)

def get_reject_dossier_use_case(session: AsyncSession = Depends(get_async_db), triage_repo: SqlTriageRepository = Depends(get_triage_repository)) -> RejectDossierUseCase:
    return RejectDossierUseCase(triage_repo=triage_repo, session=session)

def get_cases_by_batch_use_case(triage_repo: SqlTriageRepository = Depends(get_triage_repository)) -> GetCasesByBatchUseCase:
    return GetCasesByBatchUseCase(triage_repo=triage_repo)

def get_verify_batch_completion_use_case(
    session: AsyncSession = Depends(get_async_db),
    triage_repo: SqlTriageRepository = Depends(get_triage_repository)
) -> VerifyBatchCompletionUseCase:
    from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_batch_repository import SqlBatchRepository
    from src.contexts.data_quality_triage.infrastructure.adapters.batch_status_validator_adapter import BatchStatusValidatorAdapter

    batch_repo = SqlBatchRepository(session=session)
    validator = BatchStatusValidatorAdapter(batch_repository=batch_repo)
    return VerifyBatchCompletionUseCase(triage_repository=triage_repo, batch_status_validator=validator)

def get_batch_summary_use_case(triage_repo: SqlTriageRepository = Depends(get_triage_repository)) -> GetBatchSummaryUseCase:
    return GetBatchSummaryUseCase(triage_repository=triage_repo)
