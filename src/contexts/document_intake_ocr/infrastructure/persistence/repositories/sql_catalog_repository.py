from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.contexts.document_intake_ocr.domain.entities.document_type import DocumentTypeConfig
from src.contexts.document_intake_ocr.domain.repositories.document_catalog_repository import DocumentCatalogRepository
from src.contexts.document_intake_ocr.infrastructure.persistence.mappers.document_catalog_mapper import DocumentCatalogMapper
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_type_config import DocumentTypeConfigModel

class SqlDocumentCatalogRepository(DocumentCatalogRepository):
    """
    Gestor de Persistencia asíncrono para el catálogo de documentos.
    Implementación optimizada usando SQLAlchemy 2.0.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, catalog_id: int) -> Optional[DocumentTypeConfig]:
        """Recupera la configuración por su ID de forma asíncrona."""
        query = select(DocumentTypeConfigModel).filter_by(id=catalog_id)
        result = await self.session.execute(query)
        db_model = result.scalar_one_or_none()
        return DocumentCatalogMapper.to_domain(db_model) if db_model else None

    async def get_all_active(self) -> List[DocumentTypeConfig]:
        """Devuelve todos los formatos activos usando select asíncrono."""
        query = select(DocumentTypeConfigModel).filter_by(is_active=True)
        result = await self.session.execute(query)
        db_models = result.scalars().all()
        return [DocumentCatalogMapper.to_domain(model) for model in db_models]

    async def save(self, document_config: DocumentTypeConfig) -> None:
        """Guarda o actualiza de forma asíncrona."""
        db_model = DocumentCatalogMapper.to_model(document_config)
        
        # Merge en async detecta INSERT/UPDATE
        await self.session.merge(db_model)
        
        # Commit asíncrono
        await self.session.commit()

    async def get_by_ids(self, ids: List[int]) -> List[DocumentTypeConfig]:
        """
        Recupera múltiples configuraciones de documentos por una lista de IDs.
        Optimizado para realizar una sola consulta a la base de datos (Bulk Fetch).
        """
        if not ids:
            return []  
        # Si la lista está vacía, devuelve una lista vacía y no hagas query.
        # Usamos el operador .in_() para filtrar múltiples IDs en una sola consulta
        query = select(DocumentTypeConfigModel).filter(DocumentTypeConfigModel.id.in_(ids))
        result = await self.session.execute(query)
        db_models = result.scalars().all()
        return [DocumentCatalogMapper.to_domain(model) for model in db_models]