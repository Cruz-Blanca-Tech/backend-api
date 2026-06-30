from typing import List
from src.contexts.reporting_analytics.features.demographics.infrastructure.repositories.sql_demographics_repository import SqlDemographicsRepository
from src.contexts.reporting_analytics.features.demographics.presentation.schemas.school_schemas import SchoolDistributionData
from src.contexts.reporting_analytics.shared.schemas.dashboard_response import DashboardResponse

class GetSchoolDistributionUseCase:
    def __init__(self, repository: SqlDemographicsRepository):
        self.repository = repository

    async def execute(self) -> DashboardResponse[SchoolDistributionData]:
        # Target schools mapping: Main category -> List of lowercase substrings to match
        TARGET_SCHOOLS = {
            "Villas": ["villa"],
            "San Martín": ["martin", "martín"]
        }
        
        raw_data = await self.repository.get_raw_school_distribution()
        
        # Initialize buckets
        buckets = {school: 0 for school in TARGET_SCHOOLS.keys()}
        buckets["Otros"] = 0
        
        for item in raw_data:
            school_str = str(item.get("school", "") or "").lower()
            count = item.get("total", 0)
            
            matched = False
            for target_name, patterns in TARGET_SCHOOLS.items():
                if any(p in school_str for p in patterns):
                    buckets[target_name] += count
                    matched = True
                    break
            
            if not matched:
                buckets["Otros"] += count
                
        # Format for Recharts
        result_list = [SchoolDistributionData(school=k, count=v) for k, v in buckets.items() if v > 0]
        # Sort by count descending
        sorted_result = sorted(result_list, key=lambda x: x.count, reverse=True)
        return DashboardResponse(
            title="Distribución por Colegios",
            description="Distribución de beneficiarios agrupada inteligentemente por las escuelas objetivo.",
            source="vw_reporting_raw_schools (Agrupación en Capa de Aplicación)",
            data=sorted_result
        )
