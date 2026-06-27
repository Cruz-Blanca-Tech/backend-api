import logging
from collections import defaultdict
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from src.contexts.data_quality_triage.application.shared.schemas.triage_schemas import BatchProcessingResult
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.strategies.strategy_factory import DossierStrategyFactory
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageVerdict
from src.contexts.data_quality_triage.infrastructure.acl.intake_acl import IntakeACL
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel
from src.core.events.event_dispatcher import EventDispatcher
from src.core.validators.exceptions import EntityNotFoundException, DomainValidationError

logger = logging.getLogger(__name__)
SYSTEM_UUID = UUID("00000000-0000-0000-0000-000000000000")

class DossierProcessor:
    def __init__(self, triage_repo: SqlTriageRepository, intake_acl: IntakeACL, strategy_factory: DossierStrategyFactory, session: AsyncSession):
        self.triage_repo = triage_repo
        self.intake_acl = intake_acl
        self.strategy_factory = strategy_factory
        self.session = session

    async def process_batch(self, batch_id: UUID) -> BatchProcessingResult:
        activity_id = await self.intake_acl.get_activity_id_for_batch(batch_id)
        if not activity_id: raise EntityNotFoundException(f"No se encontr? el lote con ID: {batch_id}")
        documents = await self.intake_acl.get_documents_ready_for_review(batch_id)
        if not documents: raise DomainValidationError(f"No hay documentos en estado READY_FOR_REVIEW para el lote {batch_id}")

        thresholds = await self.intake_acl.get_all_thresholds_for_activity(activity_id)
        default_threshold = 0.85

        dossiers = defaultdict(list)
        for doc in documents:
            dossiers[doc.dni_reference].append(doc)

        auto_approved_count = 0
        triage_count = 0
        cases_to_save = []

        for dni, docs in dossiers.items():
            documents_snapshot = {}
            document_ids = {}
            confidence_scores = {}
            for doc in docs:
                documents_snapshot[doc.document_code] = doc.extracted_data
                document_ids[doc.document_code] = doc.id
                confidence_scores[doc.document_code] = doc.confidence_score or 0.0

            doc_thresholds = [thresholds.get(code, default_threshold) for code in documents_snapshot.keys()]
            threshold = min(doc_thresholds) if doc_thresholds else default_threshold

            strategy = self.strategy_factory.get_strategy_for_documents(set(documents_snapshot.keys()))
            quality_result = strategy.validate(dossier_documents=documents_snapshot, confidence_scores=confidence_scores, confidence_threshold=threshold)

            case = TriageCase.create_from_quality_result(
                batch_id=batch_id, dni_reference=dni, documents_snapshot=documents_snapshot,
                document_ids=document_ids, confidence_scores=confidence_scores,
                confidence_threshold=threshold, quality_result=quality_result,
            )
            cases_to_save.append(case)

            if case.verdict == TriageVerdict.AUTO_APPROVED:
                auto_approved_count += 1
            else:
                triage_count += 1

        await self.triage_repo.bulk_save(cases_to_save)

        for case in cases_to_save:
            audit_log = TriageAuditLogModel(
                id=uuid4(), triage_case_id=case.id, action="CREATED",
                performed_by=SYSTEM_UUID, previous_status=None, new_status=case.status.value,
                details={"verdict": case.verdict.value, "error_count": sum(1 for d in case.discrepancies if d.severity == "ERROR"), "warning_count": sum(1 for d in case.discrepancies if d.severity == "WARNING")},
            )
            self.session.add(audit_log)

        for case in cases_to_save:
            for event in case.pending_events:
                await EventDispatcher.dispatch(event)
            case.clear_events()

        await self.session.commit()

        return BatchProcessingResult(
            batch_id=batch_id, total_dossiers=len(dossiers), total_documents=len(documents),
            auto_approved=auto_approved_count, sent_to_triage=triage_count,
        )
