from uuid import UUID, uuid4
from typing import Dict, Any
from src.contexts.data_quality_triage.domain.entities.triage_case import TriageCase, TriageStatus
from src.contexts.data_quality_triage.domain.ports.document_provider import DocumentProvider
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_case_repository import SqlTriageCaseRepository
from src.contexts.data_quality_triage.domain.services.dossier_policy import DossierPolicy
from src.contexts.data_quality_triage.application.schemas.dossier_schemas import EducaInscriptionResponse
from src.contexts.data_quality_triage.application.factories.dossier_factory import DossierFactory

class CreateDossierUseCase:
    def __init__(
        self, 
        doc_provider: DocumentProvider, 
        case_repo: SqlTriageCaseRepository,
        policy: DossierPolicy
    ):
        self.doc_provider = doc_provider
        self.case_repo = case_repo
        self.policy = policy

    async def execute(self, activity_id: UUID, batch_id: UUID, dni: str) -> EducaInscriptionResponse:
        """
        Fase 1: Creación del Dossier a partir de los documentos extraídos.
        """
        # 1. Obtención de datos crudos
        documents = await self.doc_provider.get_documents_by_batch_and_dni(batch_id, dni)
        
        raw_docs = {}
        for doc in documents:
            raw_docs[doc.code] = doc.extracted_data

        # 2. Construir el Dossier inicial
        inscription = DossierFactory.from_data(raw_docs)

        # 3. Fase 1: Validación Cruzada (Política)
        policy_errors = self.policy.evaluate(raw_docs)
        
        # Determine Status
        status = TriageStatus.PENDING_CORRECTION if policy_errors else TriageStatus.VALID
        is_valid = len(policy_errors) == 0

        # 4. Creación de caso de triaje
        case_id = uuid4()
        case = TriageCase(
            id=case_id,
            batch_id=batch_id,
            activity_id=activity_id,
            dni_reference=dni,
            canonical_data=[inscription.to_dict()],
            is_valid=is_valid,
            status=status.value,
            missing_documents=[],
            issues=[{"description": error} for error in policy_errors]
        )
        
        await self.case_repo.save(case)
        
        return EducaInscriptionResponse(
            case_id=str(case_id),
            status=status.value,
            is_valid=is_valid,
            issues=policy_errors,
            canonical_data=inscription.to_dict()
        )
