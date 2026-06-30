from typing import List
from src.contexts.reporting_analytics.features.demographics.infrastructure.repositories.sql_demographics_repository import SqlDemographicsRepository
from src.contexts.reporting_analytics.features.demographics.presentation.schemas.registration_schemas import RegistrationGrowthData
from src.contexts.reporting_analytics.shared.schemas.dashboard_response import DashboardResponse

class GetRegistrationGrowthUseCase:
    def __init__(self, repository: SqlDemographicsRepository):
        self.repository = repository

    async def execute(self) -> DashboardResponse[RegistrationGrowthData]:
        data = await self.repository.get_registration_growth()
        result_data = [RegistrationGrowthData(**item) for item in data]
        return DashboardResponse(
            title="Crecimiento de Inscripciones",
            description="Cantidad de nuevos beneficiarios aprobados por mes.",
            source="vw_reporting_registration_growth",
            data=result_data
        )
