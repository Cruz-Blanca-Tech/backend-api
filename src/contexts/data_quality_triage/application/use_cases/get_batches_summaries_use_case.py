from typing import List, Dict
from uuid import UUID
from src.contexts.data_quality_triage.domain.shared.repositories.triage_repository import TriageRepository
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageVerdict

class GetBatchesSummariesUseCase:
    def __init__(self, triage_repository: TriageRepository):
        self.triage_repository = triage_repository

    async def execute(self, batch_ids: List[UUID]) -> Dict[UUID, dict]:
        if not batch_ids:
            return {}

        cases = await self.triage_repository.get_all_by_batch_ids(batch_ids)
        
        # Initialize default summaries for each requested batch_id
        summaries = {}
        for b_id in batch_ids:
            summaries[b_id] = {
                "total_cases": 0,
                "verdicts": {v.name: 0 for v in TriageVerdict}
            }

        # Count cases and group by verdict for each batch
        for case in cases:
            b_id = case.batch_id
            if b_id in summaries:
                summaries[b_id]["total_cases"] += 1
                verdict_name = case.verdict.name if hasattr(case.verdict, 'name') else case.verdict
                if verdict_name in summaries[b_id]["verdicts"]:
                    summaries[b_id]["verdicts"][verdict_name] += 1
                else:
                    summaries[b_id]["verdicts"][verdict_name] = 1

        return summaries
