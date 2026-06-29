from uuid import UUID
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository

class GetBatchSummaryUseCase:
    def __init__(self, triage_repository: TriageRepository):
        self.triage_repository = triage_repository

    async def execute(self, batch_id: UUID) -> dict:
        cases = await self.triage_repository.get_all_by_batch_id(batch_id)
        
        from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageVerdict
        
        verdicts = {v.name: 0 for v in TriageVerdict}

        if not cases:
            return {
                "batch_id": str(batch_id),
                "total_cases": 0,
                "verdicts": verdicts
            }
        
        for case in cases:
            verdict_name = case.verdict.name if hasattr(case.verdict, 'name') else case.verdict
            verdicts[verdict_name] = verdicts.get(verdict_name, 0) + 1
            
        return {
            "batch_id": str(batch_id),
            "total_cases": len(cases),
            "verdicts": verdicts
        }
