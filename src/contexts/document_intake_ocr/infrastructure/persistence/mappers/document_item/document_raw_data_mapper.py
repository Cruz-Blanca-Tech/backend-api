from uuid import UUID, uuid4
from datetime import datetime
from typing import Dict, Any

from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_raw_data_model import DocumentRawDataModel



class DocumentRawDataMapper:
    """
    Mapper BC2: OCR RAW DATA (Azure output)
    """

    @staticmethod
    def to_model(document_id: UUID, data: Dict[str, Any], model_id: str) -> DocumentRawDataModel:
        return DocumentRawDataModel(
            id=uuid4(),  # o uuid4()
            document_id=document_id,
            data=data,
            model_id=model_id,
            created_at=datetime.utcnow()
        )

    @staticmethod
    def to_domain(model: DocumentRawDataModel) -> Dict[str, Any]:
        return model.data