from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_db
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_analytics_repository import SqlAnalyticsRepository
from src.contexts.data_quality_triage.application.shared.schemas.analytics_schemas import (
    TriageSummaryMetricsResponse, 
    TriageIssuesResponse,
    TopIssueResponse
)

router = APIRouter(
    prefix="/api/v1/triage/analytics",
    tags=["Triage Analytics"],
    responses={404: {"description": "Not found"}}
)

@router.get("/summary", response_model=TriageSummaryMetricsResponse)
async def get_analytics_summary(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Obtiene métricas agregadas del Triaje (Total procesados, estado actual, promedio de confianza OCR).
    """
    repo = SqlAnalyticsRepository(db)
    metrics = await repo.get_summary_metrics()
    return TriageSummaryMetricsResponse(**metrics)

@router.get("/issues", response_model=TriageIssuesResponse)
async def get_top_issues(
    limit: int = 5,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Obtiene el top N de discrepancias o errores más comunes detectados por el Motor de Calidad.
    """
    repo = SqlAnalyticsRepository(db)
    issues = await repo.get_top_issues(limit)
    return TriageIssuesResponse(top_issues=[TopIssueResponse(**i) for i in issues])
