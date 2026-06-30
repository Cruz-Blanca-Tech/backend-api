from typing import List
from src.contexts.reporting_analytics.features.operations.infrastructure.repositories.sql_operations_repository import SqlOperationsRepository
from src.contexts.reporting_analytics.features.operations.presentation.schemas.success_rate_schemas import SuccessRateData
from src.contexts.reporting_analytics.shared.schemas.dashboard_response import DashboardResponse

class GetSuccessRateUseCase:
    def __init__(self, repository: SqlOperationsRepository):
        self.repository = repository

    async def execute(self) -> DashboardResponse[SuccessRateData]:
        data = await self.repository.get_success_rate()
        result_data = [SuccessRateData(**item) for item in data]
        return DashboardResponse(
            title="Tasa de Éxito del OCR",
            description="Proporción de expedientes aprobados versus rechazados por el sistema y validadores.",
            source="vw_ops_success_rate",
            legend={
                "APPROVED": "El expediente pasó todas las validaciones de calidad y fue inscrito exitosamente.",
                "REJECTED": "El expediente falló validaciones del OCR o reglas de negocio (ej. firma borrosa).",
                "PENDING": "El expediente está en cola esperando ser procesado por la Inteligencia Artificial."
            },
            data=result_data
        )
