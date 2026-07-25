from pydantic import BaseModel, Field
from src.contexts.document_intake_ocr.application.schemas.file_item_schema import FileItemSchema

class UploadMissingDocumentRequest(BaseModel):
    file: FileItemSchema = Field(..., description="Archivo físico faltante (nombre inventado por UI y source_id de nube)")
