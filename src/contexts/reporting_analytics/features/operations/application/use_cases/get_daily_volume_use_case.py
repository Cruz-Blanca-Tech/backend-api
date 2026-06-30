from typing import List
from src.contexts.reporting_analytics.features.operations.infrastructure.repositories.sql_operations_repository import SqlOperationsRepository
from src.contexts.reporting_analytics.features.operations.presentation.schemas.daily_volume_schemas import DailyVolumeData
from src.contexts.reporting_analytics.shared.schemas.dashboard_response import DashboardResponse

class GetDailyVolumeUseCase:
    def __init__(self, repository: SqlOperationsRepository):
        self.repository = repository

    async def execute(self) -> DashboardResponse[DailyVolumeData]:
        data = await self.repository.get_daily_volume()
        result_data = [DailyVolumeData(**item) for item in data]
        return DashboardResponse(
            title="Volumen de Procesamiento Diario",
            description="Línea de tiempo con la cantidad de expedientes procesados por el OCR cada día.",
            source="vw_ops_daily_volume",
            data=result_data
        )
