from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_db
from src.contexts.reporting_analytics.features.operations.infrastructure.repositories.sql_operations_repository import SqlOperationsRepository

def get_operations_repo(session: AsyncSession = Depends(get_async_db)) -> SqlOperationsRepository:
    return SqlOperationsRepository(session)
