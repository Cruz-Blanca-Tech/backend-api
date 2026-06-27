from src.contexts.data_quality_triage.domain.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.entities.triage_document import TriageDocument
from src.contexts.data_quality_triage.domain.value_objects.canonical_data import CanonicalData


class DocumentDTOToTriageDocumentMapper:

    @staticmethod
    def to_domain(self, dto:DocumentDTO, canonical_data:CanonicalData):

        return TriageDocument(
            id=dto.id,
            batch_id=dto.batch,
            document_code=dto.document_code,
            canonical_data=canonical_data,
            confidence_score=dto.confidence_score or 0.0
        )