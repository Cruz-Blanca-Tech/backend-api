import logging
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.strategies.triage_strategy_factory import TriageStrategyFactory
from src.contexts.data_quality_triage.domain.shared.repositories.document_read_repository import DocumentReadRepository
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel
from src.core.events.event_dispatcher import EventDispatcher
from src.core.validators.exceptions import EntityNotFoundException, DomainValidationError

logger = logging.getLogger(__name__)
SYSTEM_UUID = UUID("00000000-0000-0000-0000-000000000000")

class ProcessDossierUseCase:
    def __init__(
        self, 
        triage_repo: SqlTriageRepository, 
        doc_repo: DocumentReadRepository,
        strategy_factory: TriageStrategyFactory,
        session: AsyncSession
    ):
        self.triage_repo = triage_repo
        self.doc_repo = doc_repo
        self.strategy_factory = strategy_factory
        self.session = session

    async def execute(self, dni: str, batch_id: UUID, activity_type_str: str) -> TriageCase:
        # 1. Recuperar los documentos enriquecidos
        docs = await self.doc_repo.get_by_dni(batch_id=batch_id, dni_reference=dni)
        if not docs:
            logger.warning(f"No se encontraron documentos para el DNI {dni} en el lote {batch_id}")
            raise Exception("No documents found")

        # 2. 🔥 ¡Aquí entra la Actividad! La Factory decide la estrategia basándose en el contexto
        strategy = self.strategy_factory.get_strategy(
            document_codes={doc.document_code for doc in docs if doc.document_code}, 
            activity_type_str=activity_type_str
        )
        
        from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
        activity_type = ActivityType(activity_type_str)
        
        # 3. Ejecutar la validación cruzada y construir el caso
        case = strategy.execute(batch_id=batch_id, activity_type=activity_type, dni_reference=dni, documents=docs)

        # 3.5. Si ya existía un caso para este DNI en este Batch, reusar su ID para actualizarlo en lugar de duplicarlo
        existing_case = await self.triage_repo.get_by_dossier(batch_id=batch_id, dni_reference=dni)
        if existing_case:
            case.id = existing_case.id
            case.created_at = existing_case.created_at
            # Preserve resolved_by and resolved_at if someone manually corrected it before
            case.resolved_by = existing_case.resolved_by
            case.resolved_at = existing_case.resolved_at

        # 4. Persistencia y Eventos
        await self.triage_repo.save(case)
        await self._audit_and_dispatch(case)
        await self.session.commit()
        return case

    async def _audit_and_dispatch(self, case: TriageCase) -> None:
        self.session.add(TriageAuditLogModel(
            id=uuid4(), triage_case_id=case.id,
            action="CREATED", performed_by=SYSTEM_UUID,
            previous_status=None, new_status=case.status.value,
            details={
                "verdict":       case.verdict.value,
                "error_count":   sum(1 for d in case.discrepancies if d.severity == "ERROR"),
                "warning_count": sum(1 for d in case.discrepancies if d.severity == "WARNING"),
            },
        ))
        for event in case.pending_events:
            await EventDispatcher.dispatch(event)
        case.clear_events()
