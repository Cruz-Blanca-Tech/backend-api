import logging
from uuid import UUID
from src.contexts.data_quality_triage.application.shared.schemas.triage_schemas import (
    TriageCaseListItem, PaginatedTriageResponse, DiscrepancySchema
)
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository

logger = logging.getLogger(__name__)

class GetCasesByBatchUseCase:
    """Lista los casos de triaje de un lote para la UI.

    Cada item expone `confidence_threshold`: el umbral de confianza OCR más
    exigente entre los documentos del caso (según activity_requirements de la
    actividad del lote). Antes estaba hardcodeado en 0.0, con lo que la UI
    siempre mostraba "sobre umbral".
    """

    DEFAULT_THRESHOLD = 0.80

    def __init__(self, triage_repo: SqlTriageRepository):
        self.triage_repo = triage_repo

    async def execute(self, batch_id: UUID, skip: int = 0, limit: int = 100) -> PaginatedTriageResponse:
        cases, total = await self.triage_repo.list_by_batch_id(batch_id, skip=skip, limit=limit)

        # Umbrales por tipo de documento de la actividad del lote {code: umbral}.
        thresholds = {}
        try:
            thresholds = await self.triage_repo.get_confidence_thresholds(batch_id)
        except Exception:
            logger.exception("Error cargando umbrales de confianza del lote %s", batch_id)

        items = [
            TriageCaseListItem(
                id=case.id, batch_id=case.batch_id, dni_reference=case.dni_reference, status=case.status.value, verdict=case.verdict.value,
                min_confidence_score=case.min_confidence_score,
                confidence_threshold=self._effective_threshold(case, thresholds),
                error_count=sum(1 for d in case.discrepancies if d.severity == "ERROR"), warning_count=sum(1 for d in case.discrepancies if d.severity == "WARNING"),
                sync_status=case.sync_status, sync_error=case.sync_error,
                discrepancies=[DiscrepancySchema(field_name=d.field_name, expected_pattern=d.expected_pattern, actual_value=d.actual_value, rule_description=d.rule_description, severity=d.severity, document_code=d.document_code) for d in case.discrepancies],
                created_at=case.created_at, updated_at=case.updated_at,
            ) for case in cases
        ]
        return PaginatedTriageResponse(items=items, total=total, skip=skip, limit=limit)

    def _effective_threshold(self, case: "TriageCase", thresholds: dict) -> float:
        """El umbral efectivo del caso = el más exigente entre los documentos
        presentes (los que la evaluación compara). Si la actividad no define
        umbrales, se usa el default 0.80 (el mismo del engine)."""
        codes = (case.confidence_scores or {}).keys()
        vals = [thresholds.get(code) or self.DEFAULT_THRESHOLD for code in codes]
        if not vals:
            vals = [self.DEFAULT_THRESHOLD]
        return max(vals)
