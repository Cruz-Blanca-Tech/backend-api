from typing import List, Dict
from uuid import UUID
from src.contexts.document_intake_ocr.domain.ports.triage_service import TriageServicePort
from src.contexts.data_quality_triage.application.use_cases.get_batches_summaries_use_case import GetBatchesSummariesUseCase

class TriageServiceAdapter(TriageServicePort):
    def __init__(self, get_batches_summaries_use_case: GetBatchesSummariesUseCase):
        self.get_batches_summaries_use_case = get_batches_summaries_use_case

    async def get_triage_summaries(self, batch_ids: List[UUID]) -> Dict[UUID, dict]:
        return await self.get_batches_summaries_use_case.execute(batch_ids)
