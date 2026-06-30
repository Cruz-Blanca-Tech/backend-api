from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.contexts.reporting_analytics.features.operations.infrastructure.repositories.sql_operations_repository import SqlOperationsRepository
from src.contexts.reporting_analytics.features.operations.presentation.api.deps import get_operations_repo
from src.contexts.reporting_analytics.features.operations.application.use_cases.export_rejected_cases_use_case import ExportRejectedCasesUseCase
from src.contexts.reporting_analytics.features.operations.application.use_cases.export_ocr_audit_use_case import ExportOcrAuditUseCase

router = APIRouter(prefix="/operations/exports", tags=["Reporting - Operations Exports"])

@router.get("/rejected-cases")
async def export_rejected_cases(repo: SqlOperationsRepository = Depends(get_operations_repo)):
    use_case = ExportRejectedCasesUseCase(repo)
    return StreamingResponse(
        use_case.execute(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=operaciones_casos_rechazados.csv"}
    )

@router.get("/ocr-audit")
async def export_ocr_audit(repo: SqlOperationsRepository = Depends(get_operations_repo)):
    use_case = ExportOcrAuditUseCase(repo)
    return StreamingResponse(
        use_case.execute(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=operaciones_auditoria_ocr.csv"}
    )
