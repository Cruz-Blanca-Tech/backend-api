# src/contexts/document_intake_ocr/domain/entities/document_type_config.py

from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4

from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode

@dataclass
class DocumentTypeConfig:
    id: UUID
    code: DocumentTypeCode              # Ej: "FINS" (Puro, sin año)
    name: str              # Ej: "Ficha de Inscripción"
    year: int              # Ej: 2026 (El año de vigencia)
    model_id: str          # Azure Model ID
    version: int           # Versión del modelo
    preview_image_url: str
    is_active: bool = True
