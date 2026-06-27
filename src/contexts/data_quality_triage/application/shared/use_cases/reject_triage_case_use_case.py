from uuid import UUID

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageStatus
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository

class RejectTriageCaseUseCase:
    def __init__(self, case_repo: TriageRepository):
        self.case_repo = case_repo

    async def execute(self, case_id: UUID, reason: str) -> None:
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            raise ValueError(f"Triage Case {case_id} not found")

        case.status = TriageStatus.REJECTED.value
        case.is_valid = False
        if reason:
            case.issues.append({"description": f"Rejected manually: {reason}"})

        await self.case_repo.save(case)
