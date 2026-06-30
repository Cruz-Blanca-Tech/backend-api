from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from src.contexts.document_intake_ocr.domain.value_objects.dni import DNI
from src.contexts.document_intake_ocr.domain.value_objects.document_code import DocumentTypeCode

class DocumentStatus(str, Enum):
    PENDING = "PENDING"                       # Recién encolado, esperando proceso
    PROCESSING_OCR = "PROCESSING_OCR"         # Actualmente enviándose a Azure
    READY_FOR_REVIEW = "READY_FOR_REVIEW"     # Azure terminó, esperando triaje humano
    APPROVED = "APPROVED"                     # Humano validó que todo está correcto
    REJECTED = "REJECTED"                     # Humano rechazó el documento por reglas de negocio
    FAILED = "FAILED"                         # Error técnico o documento ilegible


class DocumentItem:
    """
    Entidad de Dominio que representa un documento físico digitalizado
    dentro del proceso de ingesta.
    """
    def __init__(
        self, 
        id: UUID,
        source_id: str,                     # URI de origen (Ej: storage temporal de subida)
        file_name: str,                      # Ej: "71223344_FINS.pdf"
        dni_reference: DNI,                  # Ej: "71223344"
        document_code:Optional[DocumentTypeCode]= None, # Recibe el Value Object Code   
        document_type_config_id: Optional[UUID] = None, # <-- Hazlo opcional
        status: DocumentStatus = DocumentStatus.PENDING,
        custody_id: Optional[str] = None,   # URI del almacenamiento definitivo y seguro
        extracted_data: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
        failure_reason: Optional[str] = None,
        processed_at: Optional[datetime] = None
    ):
        self.id = id
        self.document_code = document_code
        self.source_id = source_id
        self.file_name = file_name
        self.dni_reference = dni_reference
        self.document_type_config_id = document_type_config_id
        self.status = status
        self.custody_id = custody_id
        self.extracted_data = extracted_data or {}
        self.confidence_score = confidence_score
        self.failure_reason = failure_reason
        self.processed_at = processed_at

    # =========================================================
    # COMPORTAMIENTOS DEL DOMINIO (Rich Domain Model)
    # =========================================================
    
    def secure_in_custody(self, custody_id: str) -> None:
        """
        Registra la ubicación final del archivo tras ser convertido 
        y almacenado en el repositorio de custodia definitivo.
        """
        self.custody_id = custody_id

    def mark_as_processing(self) -> None:
        """
        Cambia el estado cuando el motor asíncrono (ej. Worker) 
        comienza a procesar el documento.
        """
        self.status = DocumentStatus.PROCESSING_OCR

    def mark_as_processed_successfully(self, data: Dict[str, Any], confidence: float) -> None:
        """
        Llamado cuando la IA (Azure Document Intelligence) devuelve 
        los datos estructurados correctamente.
        """
        self.status = DocumentStatus.READY_FOR_REVIEW
        self.extracted_data = data
        self.confidence_score = confidence
        self.processed_at = datetime.utcnow()
        self.failure_reason = None  # Limpiamos errores previos por si fue un reintento

    def mark_as_failed(self, reason: str) -> None:
        """
        Llamado si el archivo está corrupto, la API de Azure se cae, 
        o la imagen es ilegible.
        """
        self.status = DocumentStatus.FAILED
        self.failure_reason = reason
        self.processed_at = datetime.utcnow()

    def mark_as_approved(self) -> None:
        """
        Llamado por el Caso de Uso de Triaje cuando el supervisor 
        humano da el visto bueno a los datos extraídos.
        """
        self.status = DocumentStatus.APPROVED

    @classmethod
    def create_valid(cls, source_id: str, document_code: DocumentTypeCode, file_name: str, dni_ref: DNI, config_id: UUID) -> 'DocumentItem':
        """Constructor para documentos que pasaron el filtro."""
        return cls(
            id=uuid4(),
            source_id=source_id,
            document_code = document_code,
            file_name=file_name,
            dni_reference=dni_ref,
            document_type_config_id=config_id,
            status=DocumentStatus.PENDING
        )

    @classmethod
    def create_failed(cls, source_id: str, file_name: str, dni_ref: DNI, reason: str) -> 'DocumentItem':
        """Constructor para documentos rechazados por el filtro."""
        item = cls(
            id=uuid4(),
            source_id=source_id,
            file_name=file_name,
            dni_reference=dni_ref,
            status=DocumentStatus.FAILED
        )
        item.mark_as_failed(reason)
        return item