from typing import Optional
from src.contexts.core_beneficiary_management.domain.value_objects.historical_document import HistoricalDocument
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.historical_document_model import HistoricalDocumentModel

class HistoricalDocumentMapper:
    @staticmethod
    def to_domain(model: Optional[HistoricalDocumentModel]) -> Optional[HistoricalDocument]:
        if not model:
            return None
            
        return HistoricalDocument(
            id=model.id,
            beneficiary_id=model.beneficiary_id,
            batch_id=model.batch_id,
            document_type=model.document_type,
            year=model.year,
            file_id=model.file_id
        )

    @staticmethod
    def to_persistence(entity: Optional[HistoricalDocument], beneficiary_id) -> Optional[HistoricalDocumentModel]:
        if not entity:
            return None
            
        return HistoricalDocumentModel(
            id=entity.id,
            beneficiary_id=beneficiary_id,
            batch_id=entity.batch_id,
            document_type=entity.document_type,
            year=entity.year,
            file_id=entity.file_id
        )
