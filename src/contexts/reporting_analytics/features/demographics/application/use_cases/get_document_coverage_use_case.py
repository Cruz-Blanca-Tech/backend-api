from typing import List
from src.contexts.reporting_analytics.features.demographics.infrastructure.repositories.sql_demographics_repository import SqlDemographicsRepository
from src.contexts.reporting_analytics.features.demographics.presentation.schemas.coverage_schemas import DocumentCoverageData
from src.contexts.reporting_analytics.shared.schemas.dashboard_response import DashboardResponse

class GetDocumentCoverageUseCase:
    def __init__(self, repository: SqlDemographicsRepository):
        self.repository = repository

    async def execute(self) -> DashboardResponse[DocumentCoverageData]:
        data = await self.repository.get_document_coverage()
        result_data = [DocumentCoverageData(**item) for item in data]
        return DashboardResponse(
            title="Cobertura de Documentos",
            description="Proporción de beneficiarios que cuentan con documentos físicos frente a los que no.",
            source="vw_reporting_document_coverage",
            data=result_data
        )
