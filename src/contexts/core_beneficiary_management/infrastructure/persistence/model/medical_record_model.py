import uuid
from sqlalchemy import Boolean, String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.core.database import Base

class MedicalRecordModel(Base):
    __tablename__ = "medical_records"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("beneficiaries.id"), unique=True)
    
    has_been_hospitalized: Mapped[bool] = mapped_column(Boolean, default=False)
    hospitalization_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    has_been_operated: Mapped[bool] = mapped_column(Boolean, default=False)
    operation_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    
    vaccines: Mapped[list] = mapped_column(JSON, default=list)
    medications: Mapped[list] = mapped_column(JSON, default=list)
    allergies: Mapped[list] = mapped_column(JSON, default=list)
    diseases: Mapped[list] = mapped_column(JSON, default=list)
    insurance: Mapped[list] = mapped_column(JSON, default=list)

    beneficiary = relationship("BeneficiaryModel", back_populates="medical_record")
