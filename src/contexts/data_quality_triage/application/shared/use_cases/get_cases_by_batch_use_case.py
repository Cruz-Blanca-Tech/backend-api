import logging
from uuid import UUID
from src.contexts.data_quality_triage.application.shared.schemas.triage_schemas import (
    TriageCaseListItem, PaginatedTriageResponse, DiscrepancySchema
)
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository

logger = logging.getLogger(__name__)

class GetCasesByBatchUseCase:
    def __init__(self, triage_repo: SqlTriageRepository):
        self.triage_repo = triage_repo

    async def execute(self, batch_id: UUID, skip: int = 0, limit: int = 100) -> PaginatedTriageResponse:
        cases, total = await self.triage_repo.list_by_batch_id(batch_id, skip=skip, limit=limit)
        items = [
            TriageCaseListItem(
                id=case.id, batch_id=case.batch_id, dni_reference=case.dni_reference, status=case.status.value, verdict=case.verdict.value,
                min_confidence_score=case.min_confidence_score, confidence_threshold=case.confidence_threshold,
                error_count=sum(1 for d in case.discrepancies if d.severity == "ERROR"), warning_count=sum(1 for d in case.discrepancies if d.severity == "WARNING"),
                discrepancies=[DiscrepancySchema(field_name=d.field_name, expected_pattern=d.expected_pattern, actual_value=d.actual_value, rule_description=d.rule_description, severity=d.severity, document_code=d.document_code) for d in case.discrepancies],
                created_at=case.created_at, updated_at=case.updated_at,
            ) for case in cases
        ]
        return PaginatedTriageResponse(items=items, total=total, skip=skip, limit=limit)
