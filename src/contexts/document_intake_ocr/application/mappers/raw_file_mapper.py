# src/contexts/document_intake_ocr/application/mappers/raw_file_mapper.py

from src.contexts.document_intake_ocr.application.schemas.batch_schema import FileItemSchema
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import RawFile

class RawFileMapper:
    @staticmethod
    def to_domain(schema: FileItemSchema) -> RawFile:
        return RawFile(
            file_name=schema.file_name,
            source_id=schema.source_id
        )