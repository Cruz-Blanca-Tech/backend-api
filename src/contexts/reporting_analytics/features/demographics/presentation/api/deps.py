from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_db
from src.contexts.reporting_analytics.features.demographics.infrastructure.repositories.sql_demographics_repository import SqlDemographicsRepository

def get_demographics_repo(session: AsyncSession = Depends(get_async_db)) -> SqlDemographicsRepository:
    return SqlDemographicsRepository(session)
