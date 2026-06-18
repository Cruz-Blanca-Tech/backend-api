import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Importamos las abstracciones del Dominio
from src.contexts.document_intake_ocr.domain.entities.extraction_batch import ExtractionBatch

# Importamos los Modelos y Mappers de Infraestructura
from src.contexts.document_intake_ocr.domain.repositories.batch_repository import BatchRepository
from src.contexts.document_intake_ocr.infrastructure.persistence.mappers.batch_mapper import BatchMapper
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel

class SqlBatchRepository(BatchRepository):
    """
    Implementación concreta de IBatchRepository usando SQLAlchemy 2.0 Asíncrono.
    Maneja el Lote de Extracción como una única unidad transaccional (Aggregate Root).
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, batch: ExtractionBatch) -> None:
        """
        Inserta o actualiza el Lote y todos sus Documentos hijos.
        """
        # 1. Traducimos del mundo Puro (Dominio) al mundo SQL (Modelo)
        db_model = BatchMapper.to_model(batch)
        
        # 2. Utilizamos 'merge' para el upsert del Agregado completo.
        # SQLAlchemy se encargará inteligentemente de hacer INSERT o UPDATE
        # tanto del Batch como de los DocumentItems que vienen en la lista.
        await self.session.merge(db_model)
        
        # Opcional pero recomendado para atrapar errores de integridad antes del commit final
        await self.session.flush()
        await self.session.commit()
        

    async def get_by_id(self, batch_id: uuid.UUID) -> Optional[ExtractionBatch]:
        """
        Obtiene el Lote completo hidratando sus documentos hijos.
        """
        stmt = (
            select(ExtractionBatchModel)
            .options(selectinload(ExtractionBatchModel.documents)) # <--- Evita el error MissingGreenlet
            .where(ExtractionBatchModel.id == batch_id)
        )
        
        result = await self.session.execute(stmt)
        db_model = result.scalar_one_or_none()
        
        if not db_model:
            return None
            
        # Traducimos de vuelta al mundo Puro antes de dárselo al Caso de Uso
        return BatchMapper.to_domain(db_model)

    async def get_by_document_id(self, document_id: uuid.UUID) -> Optional[ExtractionBatch]:
        """
        Busca al "Padre" (Batch) a través del ID de un "Hijo" (DocumentItem).
        Vital para los webhooks asíncronos de Azure.
        """
        stmt = (
            select(ExtractionBatchModel)
            .join(ExtractionBatchModel.documents)
            .options(selectinload(ExtractionBatchModel.documents))
            .where(DocumentItemModel.id == document_id)
        )
        
        result = await self.session.execute(stmt)
        db_model = result.scalar_one_or_none()
        
        if not db_model:
            return None
            
        return BatchMapper.to_domain(db_model)