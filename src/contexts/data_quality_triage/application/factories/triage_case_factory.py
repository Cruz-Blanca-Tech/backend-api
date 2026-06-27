from uuid import uuid4
from typing import List, Dict
from src.contexts.data_quality_triage.application.services.canonicalizer import Canonicalizer
from src.contexts.data_quality_triage.domain.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.value_objects.canonical_data import CanonicalData
from src.contexts.data_quality_triage.application.mappers.event_to_triage_document_mapper import DocumentDTOToTriageDocumentMapper

class TriageCaseFactory:
    
    @staticmethod
    def create_from_extracted_data(
        dtos: List[DocumentDTO],
        batch_id: str,
        activity_id: str,
        dni_reference: str,
        canonicalizer: Canonicalizer
    ) -> TriageCase:

        case_id= uuid4()
        case = TriageCase(
            id=case_id,
            batch_id=batch_id,
            activity_id=activity_id,
            dni_reference=dni_reference
        )

        for dto in dtos:
            canonical = canonicalizer.build(dto.extracted_data)
            triage_doc = DocumentDTOToTriageDocumentMapper.to_domain(dto, canonical, case_id)
            case.add_document(triage_doc)

        return case