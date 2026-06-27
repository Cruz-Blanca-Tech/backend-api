from uuid import UUID

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageStatus
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository

class ApproveTriageCaseUseCase:
    def __init__(self, case_repo: TriageRepository):
        self.case_repo = case_repo

    async def execute(self, case_id: UUID) -> None:
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            raise ValueError(f"Triage Case {case_id} not found")

        case.status = TriageStatus.RESOLVED_MANUAL.value
        case.is_valid = True
        case.issues = []

        await self.case_repo.save(case)
