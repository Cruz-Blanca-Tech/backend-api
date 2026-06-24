from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_db
from src.contexts.data_quality_triage.infrastructure.acl.intake_acl import IntakeACL
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.domain.strategies.strategy_factory import DossierStrategyFactory
from src.contexts.data_quality_triage.application.services.dossier_processor import DossierProcessor
from src.contexts.data_quality_triage.application.services.triage_correction_service import TriageCorrectionService
from src.contexts.data_quality_triage.application.services.triage_query_service import TriageQueryService

def get_intake_acl(session: AsyncSession = Depends(get_async_db)) -> IntakeACL:
    return IntakeACL(session=session)

def get_triage_repository(session: AsyncSession = Depends(get_async_db)) -> SqlTriageRepository:
    return SqlTriageRepository(session=session)

def get_strategy_factory() -> DossierStrategyFactory:
    return DossierStrategyFactory()

def get_dossier_processor(session: AsyncSession = Depends(get_async_db), triage_repo: SqlTriageRepository = Depends(get_triage_repository), intake_acl: IntakeACL = Depends(get_intake_acl)) -> DossierProcessor:
    return DossierProcessor(triage_repo=triage_repo, intake_acl=intake_acl, strategy_factory=DossierStrategyFactory(), session=session)

def get_triage_correction_service(session: AsyncSession = Depends(get_async_db), triage_repo: SqlTriageRepository = Depends(get_triage_repository)) -> TriageCorrectionService:
    return TriageCorrectionService(triage_repo=triage_repo, strategy_factory=DossierStrategyFactory(), session=session)

def get_triage_query_service(session: AsyncSession = Depends(get_async_db), triage_repo: SqlTriageRepository = Depends(get_triage_repository)) -> TriageQueryService:
    return TriageQueryService(triage_repo=triage_repo, session=session)
