from uuid import UUID
from datetime import datetime
from typing import Dict, Any

from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_canonical_model import DocumentCanonicalDataModel



class DocumentCanonicalDataMapper:
    """
    Mapper BC3: datos normalizados para reglas de negocio
    """

    @staticmethod
    def to_model(
        document_id: UUID,
        canonical_data: Dict[str, Any],
        schema_version: str = "v1"
    ) -> DocumentCanonicalDataModel:

        return DocumentCanonicalDataModel(
            id=UUID(),
            document_id=document_id,
            data=canonical_data,
            schema_version=schema_version,
            created_at=datetime.utcnow()
        )

    @staticmethod
    def to_domain(model: DocumentCanonicalDataModel) -> Dict[str, Any]:
        return model.data