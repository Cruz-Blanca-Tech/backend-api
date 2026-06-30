import uuid
from typing import List
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.contexts.core_beneficiary_management.infrastructure.persistence.model.person_model import PersonModel

class BeneficiaryModel(PersonModel):
    __tablename__ = "beneficiaries"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "beneficiary",
    }

    medical_record = relationship("MedicalRecordModel", back_populates="beneficiary", uselist=False, cascade="all, delete-orphan")
    education_record = relationship("EducationRecordModel", back_populates="beneficiary", uselist=False, cascade="all, delete-orphan")
    
    # Use foreign_keys if AdultModel also has an id ForeignKey("persons.id")
    # Adults belonging to this beneficiary
    relatives: Mapped[List["AdultModel"]] = relationship("AdultModel", back_populates="beneficiary", cascade="all, delete-orphan", foreign_keys="[AdultModel.beneficiary_id]")
    
    historical_documents: Mapped[List["HistoricalDocumentModel"]] = relationship("HistoricalDocumentModel", back_populates="beneficiary", cascade="all, delete-orphan")
    enrollments: Mapped[List["EnrollmentModel"]] = relationship("EnrollmentModel", back_populates="beneficiary", cascade="all, delete-orphan")
