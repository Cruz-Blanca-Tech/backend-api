from uuid import UUID, uuid4
from typing import Dict, Any
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.domain.shared.ports.document_provider import DocumentProvider
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.domain.shared.services.dossier_policy import DossierPolicy
from src.contexts.data_quality_triage.application.educa.schemas.educa_schemas import EducaInscriptionResponse
from src.contexts.data_quality_triage.application.shared.factories.dossier_factory import DossierFactory

class CreateDossierUseCase:
    def __init__(
        self, 
        doc_provider: DocumentProvider, 
        case_repo: TriageRepository,
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
            raw_docs[doc.document_code] = doc.extracted_data

        # 2. Construir el Dossier inicial
        inscription = DossierFactory.from_data(raw_docs)

        # 3. Fase 1: Validación Cruzada (Política)
        policy_errors = self.policy.evaluate(raw_docs)
        
        # Determine Status
        status = TriageStatus.PENDING_REVIEW if policy_errors else TriageStatus.APPROVED
        verdict = TriageVerdict.REQUIRES_TRIAGE if policy_errors else TriageVerdict.AUTO_APPROVED

        # 4. Creación de caso de triaje
        from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
        
        discrepancies = []
        for error in policy_errors:
            # Fake discrepancy for policy errors
            discrepancies.append(FieldDiscrepancy(
                field_name="cross_validation",
                expected_pattern="policy_match",
                actual_value="mismatch",
                rule_description=error,
                severity="ERROR",
                document_code="MULTIPLE"
            ))

        case_id = uuid4()
        case = TriageCase(
            id=case_id,
            batch_id=batch_id,
            dni_reference=dni,
            documents_snapshot=raw_docs,
            document_ids={doc.document_code: getattr(doc, "document_id", doc.id) for doc in documents},
            confidence_scores={doc.document_code: getattr(doc, "confidence_score", 1.0) for doc in documents},
            confidence_threshold=0.8,
            status=status,
            verdict=verdict,
            discrepancies=discrepancies,
            corrected_data={}
        )
        
        await self.case_repo.save(case)
        
        return EducaInscriptionResponse(
            case_id=str(case_id),
            status=status.value,
            is_valid=len(policy_errors) == 0,
            issues=policy_errors,
            canonical_data=inscription.to_dict()
        )
