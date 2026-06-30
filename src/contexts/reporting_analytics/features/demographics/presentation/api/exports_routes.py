from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.contexts.reporting_analytics.features.demographics.infrastructure.repositories.sql_demographics_repository import SqlDemographicsRepository
from src.contexts.reporting_analytics.features.demographics.presentation.api.deps import get_demographics_repo
from src.contexts.reporting_analytics.features.demographics.application.use_cases.export_beneficiaries_csv_use_case import ExportBeneficiariesCsvUseCase

router = APIRouter(prefix="/demographics/exports", tags=["Reporting - Demographics Exports"])

@router.get("/beneficiaries-master")
async def export_beneficiaries_master(repo: SqlDemographicsRepository = Depends(get_demographics_repo)):
    use_case = ExportBeneficiariesCsvUseCase(repo)
    return StreamingResponse(
        use_case.execute(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reporte_maestro_beneficiarios.csv"}
    )
