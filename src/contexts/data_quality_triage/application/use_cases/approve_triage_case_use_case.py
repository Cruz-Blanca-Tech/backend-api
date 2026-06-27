from uuid import UUID

from src.contexts.data_quality_triage.domain.entities.triage_case import TriageStatus
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_case_repository import SqlTriageCaseRepository

class ApproveTriageCaseUseCase:
    def __init__(self, case_repo: SqlTriageCaseRepository):
        self.case_repo = case_repo

    async def execute(self, case_id: UUID) -> None:
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            raise ValueError(f"Triage Case {case_id} not found")

        # Overriding system validations to force approval
        case.status = TriageStatus.RESOLVED_MANUAL.value
        case.is_valid = True
        case.issues = []

        await self.case_repo.save(case)
