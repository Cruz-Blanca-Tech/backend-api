from typing import List
from src.contexts.core_beneficiary_management.domain.value_objects.historical_document import HistoricalDocument
from src.contexts.core_beneficiary_management.presentation.schemas.historical_document_schemas import HistoricalDocumentResponse

class HistoricalDocumentDtoMapper:
    @staticmethod
    def to_response_list(domain_entities: List[HistoricalDocument]) -> List[HistoricalDocumentResponse]:
        return [
            HistoricalDocumentResponse(
                id=doc.id,
                batch_id=doc.batch_id,
                document_type=doc.document_type,
                year=doc.year,
                file_id=doc.file_id
            )
            for doc in domain_entities
        ]
