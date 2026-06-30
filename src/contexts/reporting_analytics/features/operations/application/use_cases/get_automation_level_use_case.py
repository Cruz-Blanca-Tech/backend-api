from typing import List
from src.contexts.reporting_analytics.features.operations.infrastructure.repositories.sql_operations_repository import SqlOperationsRepository
from src.contexts.reporting_analytics.features.operations.presentation.schemas.automation_level_schemas import AutomationLevelData
from src.contexts.reporting_analytics.shared.schemas.dashboard_response import DashboardResponse

class GetAutomationLevelUseCase:
    def __init__(self, repository: SqlOperationsRepository):
        self.repository = repository

    async def execute(self) -> DashboardResponse[AutomationLevelData]:
        data = await self.repository.get_automation_level()
        result_data = [AutomationLevelData(**item) for item in data]
        return DashboardResponse(
            title="Nivel de Automatización",
            description="Cantidad de casos resueltos automáticamente por el OCR vs los que requirieron intervención manual.",
            source="vw_ops_automation_level",
            data=result_data
        )
