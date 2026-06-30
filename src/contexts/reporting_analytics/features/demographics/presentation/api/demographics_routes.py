from fastapi import APIRouter, Depends
from typing import List

from src.contexts.reporting_analytics.features.demographics.infrastructure.repositories.sql_demographics_repository import SqlDemographicsRepository
from src.contexts.reporting_analytics.features.demographics.presentation.api.deps import get_demographics_repo

from src.contexts.reporting_analytics.features.demographics.application.use_cases.get_population_pyramid_use_case import GetPopulationPyramidUseCase
from src.contexts.reporting_analytics.features.demographics.application.use_cases.get_registration_growth_use_case import GetRegistrationGrowthUseCase
from src.contexts.reporting_analytics.features.demographics.application.use_cases.get_document_coverage_use_case import GetDocumentCoverageUseCase
from src.contexts.reporting_analytics.features.demographics.application.use_cases.get_school_distribution_use_case import GetSchoolDistributionUseCase

from src.contexts.reporting_analytics.features.demographics.presentation.schemas.population_schemas import PopulationPyramidData
from src.contexts.reporting_analytics.features.demographics.presentation.schemas.registration_schemas import RegistrationGrowthData
from src.contexts.reporting_analytics.features.demographics.presentation.schemas.coverage_schemas import DocumentCoverageData
from src.contexts.reporting_analytics.features.demographics.presentation.schemas.school_schemas import SchoolDistributionData
from src.contexts.reporting_analytics.shared.schemas.dashboard_response import DashboardResponse

router = APIRouter(prefix="/demographics", tags=["Reporting - Demographics"])

@router.get("/population-pyramid", response_model=DashboardResponse[PopulationPyramidData])
async def get_population_pyramid(repo: SqlDemographicsRepository = Depends(get_demographics_repo)):
    use_case = GetPopulationPyramidUseCase(repo)
    return await use_case.execute()

@router.get("/registration-growth", response_model=DashboardResponse[RegistrationGrowthData])
async def get_registration_growth(repo: SqlDemographicsRepository = Depends(get_demographics_repo)):
    use_case = GetRegistrationGrowthUseCase(repo)
    return await use_case.execute()

@router.get("/document-coverage", response_model=DashboardResponse[DocumentCoverageData])
async def get_document_coverage(repo: SqlDemographicsRepository = Depends(get_demographics_repo)):
    use_case = GetDocumentCoverageUseCase(repo)
    return await use_case.execute()

@router.get("/school-distribution", response_model=DashboardResponse[SchoolDistributionData])
async def get_school_distribution(repo: SqlDemographicsRepository = Depends(get_demographics_repo)):
    use_case = GetSchoolDistributionUseCase(repo)
    return await use_case.execute()
