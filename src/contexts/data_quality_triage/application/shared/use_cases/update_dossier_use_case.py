from uuid import UUID
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageStatus
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.application.educa.schemas.educa_schemas import EducaInscriptionRequest, EducaInscriptionResponse
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription import EducaInscription
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.educa.value_objects.parents_data import ParentsData
from src.contexts.data_quality_triage.domain.educa.value_objects.parent_detail import ParentDetail
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData

class UpdateDossierUseCase:
    def __init__(self, case_repo: TriageRepository):
        self.case_repo = case_repo

    async def execute(self, case_id: UUID, request: EducaInscriptionRequest) -> EducaInscriptionResponse:
        """
        Fase 2: Edición y Validación Final de Completitud.
        """
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            raise ValueError(f"Triage Case {case_id} not found")

        # Reconstruct Domain Entity from Request
        beneficiary = BeneficiaryData(**request.beneficiary)
        
        parents_data = request.parents
        father = ParentDetail(**parents_data.get("father", {})) if parents_data.get("father") else None
        mother = ParentDetail(**parents_data.get("mother", {})) if parents_data.get("mother") else None
        guardian = ParentDetail(**parents_data.get("guardian", {})) if parents_data.get("guardian") else None
        
        parents = ParentsData(
            father=father,
            mother=mother,
            guardian=guardian,
            apoderado_type=parents_data.get("apoderado_type")
        )
        
        education = EducationData(**request.education)
        medical = MedicalData(**request.medical)

        inscription = EducaInscription(
            beneficiary=beneficiary,
            parents=parents,
            education=education,
            medical=medical
        )

        # Fase 2: Validación Final (Completitud)
        is_valid, issues = inscription.validate_completeness()

        # Update case
        case.is_valid = is_valid
        if is_valid:
            case.status = TriageStatus.VALID.value
            case.issues = []
        else:
            # Keeps it in INVALID state or PENDING_CORRECTION
            case.status = TriageStatus.INVALID.value
            case.issues = [{"description": issue} for issue in issues]

        case.canonical_data = [inscription.to_dict()]

        await self.case_repo.save(case)

        return EducaInscriptionResponse(
            case_id=str(case.id),
            status=case.status,
            is_valid=case.is_valid,
            issues=issues,
            canonical_data=inscription.to_dict()
        )
