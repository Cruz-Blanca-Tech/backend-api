
from uuid import UUID

from src.contexts.data_quality_triage.domain.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.ports.document_provider import DocumentProvider
from src.contexts.data_quality_triage.domain.repositories.triage_repository import TriageRepository


class CreateTriageCaseUseCase:
    def __init__(self, document_provider: DocumentProvider, triage_repo: TriageRepository):
        self.document_provider = document_provider
        self.triage_repo = triage_repo

    async def execute(self, dossier_id: UUID, dni: str) -> None:
        # El caso de uso solo conoce la interfaz
        docs = await self.document_provider.get_documents_by_dossier(dossier_id)
        
        # Lógica pura de dominio
        triage_case = TriageCase.create(dossier_id, dni, docs)
        
        await self.triage_repo.save(triage_case)