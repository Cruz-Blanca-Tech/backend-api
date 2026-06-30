from typing import List
from src.contexts.reporting_analytics.features.demographics.infrastructure.repositories.sql_demographics_repository import SqlDemographicsRepository
from src.contexts.reporting_analytics.features.demographics.presentation.schemas.population_schemas import PopulationPyramidData
from src.contexts.reporting_analytics.shared.schemas.dashboard_response import DashboardResponse

class GetPopulationPyramidUseCase:
    def __init__(self, repository: SqlDemographicsRepository):
        self.repository = repository

    async def execute(self) -> DashboardResponse[PopulationPyramidData]:
        data = await self.repository.get_population_pyramid()
        result_data = [PopulationPyramidData(**item) for item in data]
        return DashboardResponse(
            title="Pirámide Poblacional",
            description="Distribución por edad y género de los beneficiarios activos.",
            source="vw_reporting_population_pyramid",
            data=result_data
        )
