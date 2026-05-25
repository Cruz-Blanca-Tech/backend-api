from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from src.core.config import settings

# 1. Crear el motor asíncrono (SQLAlchemy 2.0)
engine = create_async_engine(
    settings.ASYNC_DATABASE_URI,
    echo=settings.ENVIRONMENT == "development",
    future=True,
)

# 2. Configurar la factoría de sesiones asíncronas
async_session_maker = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# 3. Clase base declarativa para modelos del dominio (SQLAlchemy 2.0)
class Base(DeclarativeBase):
    pass

# 4. Dependencia para inyección de dependencias en endpoints de FastAPI
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
