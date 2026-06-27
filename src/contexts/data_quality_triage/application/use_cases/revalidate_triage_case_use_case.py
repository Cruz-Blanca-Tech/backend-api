from typing import Dict, Any
from uuid import UUID

from src.contexts.data_quality_triage.domain.entities.triage_case import TriageStatus
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_case_repository import SqlTriageCaseRepository
from src.contexts.data_quality_triage.domain.value_objects.educa_inscription import EducaInscription
from src.contexts.data_quality_triage.domain.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.value_objects.parents_data import ParentsData
from src.contexts.data_quality_triage.domain.value_objects.parent_detail import ParentDetail
from src.contexts.data_quality_triage.domain.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.value_objects.medical_data import MedicalData

class RevalidateTriageCaseUseCase:
    def __init__(self, case_repo: SqlTriageCaseRepository):
        self.case_repo = case_repo

    async def execute(self, case_id: UUID) -> None:
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            raise ValueError(f"Triage Case {case_id} not found")

        # Assume canonical_data[0] contains the dossier dictionary
        if not case.canonical_data:
            raise ValueError(f"Triage Case {case_id} has no canonical data to validate")

        dossier_payload = case.canonical_data[0]

        beneficiary = BeneficiaryData(**dossier_payload.get("beneficiary", {}))
        
        parents_data = dossier_payload.get("parents", {})
        father = ParentDetail(**parents_data.get("father", {})) if parents_data.get("father") else None
        mother = ParentDetail(**parents_data.get("mother", {})) if parents_data.get("mother") else None
        guardian = ParentDetail(**parents_data.get("guardian", {})) if parents_data.get("guardian") else None
        
        parents = ParentsData(
            father=father,
            mother=mother,
            guardian=guardian,
            apoderado_type=parents_data.get("apoderado_type")
        )
        
        education = EducationData(**dossier_payload.get("education", {}))
        medical = MedicalData(**dossier_payload.get("medical", {}))

        inscription = EducaInscription(
            beneficiary=beneficiary,
            parents=parents,
            education=education,
            medical=medical
        )

        is_valid, issues = inscription.validate_completeness()

        # Update case
        case.is_valid = is_valid
        if is_valid:
            case.status = TriageStatus.VALID.value
            case.issues = []
        else:
            case.status = TriageStatus.INVALID.value
            case.issues = [{"description": issue} for issue in issues]

        case.canonical_data = [inscription.to_dict()]

        await self.case_repo.save(case)
