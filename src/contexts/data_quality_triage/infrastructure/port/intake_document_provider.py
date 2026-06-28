import logging
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.contexts.data_quality_triage.domain.shared.ports.document_provider import DocumentProvider
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel

logger = logging.getLogger(__name__)

class IntakeDocumentProvider(DocumentProvider):
    """
    Adaptador de Infraestructura (ACL - Anticorruption Layer).
    Cruza la frontera hacia el Bounded Context de OCR para consultar los documentos
    sin acoplar la lógica de negocio de Triage a las entidades de OCR.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_documents_by_batch_and_dni(self, batch_id: UUID, dni: str) -> List[DocumentDTO]:
        logger.info(f"[ACL] Consultando documentos en OCR para Batch: {batch_id}, DNI: {dni}")
        
        stmt = select(DocumentItemModel).where(
            DocumentItemModel.batch_id == batch_id,
            DocumentItemModel.dni_reference == dni
        )
        result = await self.session.execute(stmt)
        docs = result.scalars().all()
        
        # Mapeamos la entidad externa hacia el DTO puro de nuestro dominio
        dtos = []
        for doc in docs:
            # En caso de que OCR no guardara confidence, usamos 1.0 por defecto
            confidence = doc.confidence_score if hasattr(doc, 'confidence_score') and doc.confidence_score is not None else 1.0
            dtos.append(
                DocumentDTO(
                    id=doc.id,
                    document_code=doc.code or "UNKNOWN",
                    file_name=doc.file_name,
                    extracted_data=doc.extracted_data or {},
                    confidence_score=confidence
                )
            )
            
        logger.info(f"[ACL] Se mapearon {len(dtos)} documentos hacia DTOs de Triage.")
        return dtos
