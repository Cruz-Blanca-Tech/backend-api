# src/contexts/data_quality_triage/infrastructure/adapters/intake_db_provider.py
#ACL

from typing import List
from uuid import UUID

from src.contexts.data_quality_triage.domain.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.ports.document_provider import DocumentProvider


class IntakeDatabaseProvider(DocumentProvider):
    """
    Este es el ACL real. Implementa la interfaz de negocio
    usando SQL para cruzar la frontera hacia el BC2.
    """
    def __init__(self, session):
        self.session = session

    async def get_documents_by_dossier(self, dossier_id: UUID) -> List[DocumentDTO]:
        # Aquí haces la query a la tabla del BC2.
        # El dominio de BC3 está feliz y ajeno a este SQL.
        ...