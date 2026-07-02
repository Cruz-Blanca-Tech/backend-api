import asyncio
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.document_intake_ocr.domain.ports.document_storage import DocumentStorage
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel


@dataclass
class DocumentImage:
    """Bytes de una imagen de custodia listos para servir por HTTP."""
    content: bytes
    media_type: str
    file_name: str


def _media_type_for(file_name: str) -> str:
    """MIME a partir de la extensión (mismo criterio que copy_to_custody)."""
    lowered = file_name.lower()
    if lowered.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lowered.endswith(".png"):
        return "image/png"
    if lowered.endswith(".pdf"):
        return "application/pdf"
    return "application/octet-stream"


class GetDocumentImageUseCase:
    """
    Query Use Case: devuelve los BYTES de la imagen de un documento del expediente,
    descargándolos de la bóveda de Custodia con las credenciales del Robot
    (cuenta de servicio), no con las del operador.

    El frontend nunca recibe el `custody_id`: solo pide por `document_id` y el
    backend resuelve el acceso, preservando la privacidad de la bóveda (estas
    imágenes NO son públicas, a diferencia de las de "documentos esperados").
    """

    def __init__(self, storage: DocumentStorage, session: AsyncSession):
        self.storage = storage
        self.session = session

    async def execute(
        self, batch_id: UUID, dni_reference: str, document_id: UUID
    ) -> Optional[DocumentImage]:
        # Se exige que el documento pertenezca a ese lote + DNI: evita que un
        # `document_id` suelto acceda a la imagen de otro expediente.
        stmt = select(DocumentItemModel).where(
            DocumentItemModel.id == document_id,
            DocumentItemModel.batch_id == batch_id,
            DocumentItemModel.dni_reference == dni_reference,
        )
        result = await self.session.execute(stmt)
        doc = result.scalar_one_or_none()

        if doc is None or not doc.custody_id:
            return None

        # `download_file_to_memory` es SÍNCRONO (usa la API de Google en modo
        # bloqueante); lo delegamos a un hilo para no bloquear el event loop.
        content = await asyncio.to_thread(
            self.storage.download_file_to_memory, doc.custody_id
        )
        return DocumentImage(
            content=content,
            media_type=_media_type_for(doc.file_name),
            file_name=doc.file_name,
        )
