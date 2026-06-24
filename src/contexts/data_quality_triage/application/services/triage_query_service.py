import logging
from typing import List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.contexts.data_quality_triage.application.schemas.triage_schemas import (
    TriageCaseListItem, TriageCaseDetailResponse, PaginatedTriageResponse, BatchTriageSummary, FieldMetadataSchema, DiscrepancySchema, AuditLogEntry,
)
from src.contexts.data_quality_triage.domain.strategies.strategy_factory import DossierStrategyFactory
from src.contexts.data_quality_triage.domain.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel
from src.core.validators.exceptions import EntityNotFoundException

logger = logging.getLogger(__name__)

class TriageQueryService:
    def __init__(self, triage_repo: SqlTriageRepository, session: AsyncSession):
        self.triage_repo = triage_repo
        self.session = session

    async def get_triage_inbox(self, skip: int = 0, limit: int = 20) -> PaginatedTriageResponse:
        cases, total = await self.triage_repo.list_pending(skip=skip, limit=limit)
        items = [
            TriageCaseListItem(
                id=case.id, batch_id=case.batch_id, dni_reference=case.dni_reference, status=case.status.value, verdict=case.verdict.value,
                min_confidence_score=case.min_confidence_score, confidence_threshold=case.confidence_threshold,
                error_count=sum(1 for d in case.discrepancies if d.severity == "ERROR"), warning_count=sum(1 for d in case.discrepancies if d.severity == "WARNING"),
                created_at=case.created_at, updated_at=case.updated_at,
            ) for case in cases
        ]
        return PaginatedTriageResponse(items=items, total=total, skip=skip, limit=limit)

    async def get_case_detail(self, case_id: UUID) -> TriageCaseDetailResponse:
        case = await self.triage_repo.get_by_id(case_id)
        if not case: raise EntityNotFoundException(f"No se encontr? el caso de triaje con ID: {case_id}")

        strategy = DossierStrategyFactory.get_strategy_for_documents(set(case.documents_snapshot.keys()))
        field_defs = strategy.get_field_definitions()
        effective = case.effective_data
        metadata_schema = {}

        for doc_code, doc_data in effective.items():
            if doc_code == "FINS" and field_defs:
                fields_with_values = []
                for fd in field_defs:
                    fields_with_values.append(FieldMetadataSchema(name=fd["name"], type=fd["type"], label=fd["label"], value=doc_data.get(fd["name"]), is_editable=fd.get("is_editable", True), options=fd.get("options"), group=fd.get("group")))
                metadata_schema[doc_code] = fields_with_values
            else:
                dynamic_fields = [FieldMetadataSchema(name=key, type="text", label=key.replace("_", " ").title(), value=value, is_editable=True) for key, value in doc_data.items()]
                metadata_schema[doc_code] = dynamic_fields

        discrepancies = [DiscrepancySchema(field_name=d.field_name, expected_pattern=d.expected_pattern, actual_value=d.actual_value, rule_description=d.rule_description, severity=d.severity, document_code=d.document_code) for d in case.discrepancies]

        return TriageCaseDetailResponse(
            id=case.id, batch_id=case.batch_id, dni_reference=case.dni_reference, status=case.status.value, verdict=case.verdict.value,
            confidence_scores=case.confidence_scores, confidence_threshold=case.confidence_threshold, documents_snapshot=case.documents_snapshot,
            corrected_data=case.corrected_data, effective_data=case.effective_data, metadata_schema=metadata_schema, discrepancies=discrepancies,
            rejection_reason=case.rejection_reason, resolved_by=case.resolved_by, resolved_at=case.resolved_at, created_at=case.created_at, updated_at=case.updated_at,
        )

    async def get_batch_summary(self, batch_id: UUID) -> BatchTriageSummary:
        cases, _ = await self.triage_repo.list_by_batch_id(batch_id, skip=0, limit=10000)
        auto_approved = sum(1 for c in cases if c.verdict == TriageVerdict.AUTO_APPROVED)
        pending = sum(1 for c in cases if c.status in (TriageStatus.PENDING_REVIEW, TriageStatus.IN_REVIEW, TriageStatus.CORRECTED))
        manually_approved = sum(1 for c in cases if c.verdict == TriageVerdict.MANUALLY_APPROVED)
        rejected = sum(1 for c in cases if c.verdict in (TriageVerdict.MANUALLY_REJECTED,))
        return BatchTriageSummary(batch_id=batch_id, total_dossiers=len(cases), auto_approved=auto_approved, pending_review=pending, manually_approved=manually_approved, rejected=rejected)

    async def get_audit_trail(self, case_id: UUID) -> List[AuditLogEntry]:
        stmt = select(TriageAuditLogModel).where(TriageAuditLogModel.triage_case_id == case_id).order_by(TriageAuditLogModel.created_at.asc())
        logs = (await self.session.execute(stmt)).scalars().all()
        return [AuditLogEntry(id=log.id, action=log.action, performed_by=log.performed_by, previous_status=log.previous_status, new_status=log.new_status, details=log.details, created_at=log.created_at) for log in logs]
