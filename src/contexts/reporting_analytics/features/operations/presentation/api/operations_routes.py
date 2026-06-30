from fastapi import APIRouter, Depends
from typing import List

from src.contexts.reporting_analytics.features.operations.infrastructure.repositories.sql_operations_repository import SqlOperationsRepository
from src.contexts.reporting_analytics.features.operations.presentation.api.deps import get_operations_repo

from src.contexts.reporting_analytics.features.operations.application.use_cases.get_success_rate_use_case import GetSuccessRateUseCase
from src.contexts.reporting_analytics.features.operations.application.use_cases.get_automation_level_use_case import GetAutomationLevelUseCase
from src.contexts.reporting_analytics.features.operations.application.use_cases.get_daily_volume_use_case import GetDailyVolumeUseCase

from src.contexts.reporting_analytics.features.operations.presentation.schemas.success_rate_schemas import SuccessRateData
from src.contexts.reporting_analytics.features.operations.presentation.schemas.automation_level_schemas import AutomationLevelData
from src.contexts.reporting_analytics.features.operations.presentation.schemas.daily_volume_schemas import DailyVolumeData
from src.contexts.reporting_analytics.shared.schemas.dashboard_response import DashboardResponse

router = APIRouter(prefix="/operations", tags=["Reporting - Operations"])

@router.get("/success-rate", response_model=DashboardResponse[SuccessRateData])
async def get_success_rate(repo: SqlOperationsRepository = Depends(get_operations_repo)):
    use_case = GetSuccessRateUseCase(repo)
    return await use_case.execute()

@router.get("/automation-level", response_model=DashboardResponse[AutomationLevelData])
async def get_automation_level(repo: SqlOperationsRepository = Depends(get_operations_repo)):
    use_case = GetAutomationLevelUseCase(repo)
    return await use_case.execute()

@router.get("/daily-volume", response_model=DashboardResponse[DailyVolumeData])
async def get_daily_volume(repo: SqlOperationsRepository = Depends(get_operations_repo)):
    use_case = GetDailyVolumeUseCase(repo)
    return await use_case.execute()
