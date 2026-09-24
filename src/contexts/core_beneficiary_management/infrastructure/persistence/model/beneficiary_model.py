import uuid
from typing import List
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.contexts.core_beneficiary_management.infrastructure.persistence.model.person_model import PersonModel
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.person_relationship_model import PersonRelationshipModel

class BeneficiaryModel(PersonModel):
    __tablename__ = "beneficiaries"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "beneficiary",
    }

    baptized: Mapped[bool] = mapped_column(nullable=True)
    first_communion: Mapped[bool] = mapped_column(nullable=True)
    haircut_permission: Mapped[bool] = mapped_column(nullable=True)
    medical_exams_permission: Mapped[bool] = mapped_column(nullable=True)

    medical_record = relationship("MedicalRecordModel", back_populates="beneficiary", uselist=False, cascade="all, delete-orphan")
    education_record = relationship("EducationRecordModel", back_populates="beneficiary", uselist=False, cascade="all, delete-orphan")
    
    # Adults belonging to this beneficiary (Many-to-Many via generic Person relationships)
    relatives: Mapped[List["AdultModel"]] = relationship(
        "AdultModel",
        secondary="person_relationships",
        primaryjoin="BeneficiaryModel.id == foreign(PersonRelationshipModel.from_person_id)",
        secondaryjoin="AdultModel.id == foreign(PersonRelationshipModel.to_person_id)",
        back_populates="beneficiaries"
    )
    
    historical_documents: Mapped[List["HistoricalDocumentModel"]] = relationship("HistoricalDocumentModel", back_populates="beneficiary", cascade="all, delete-orphan")
    enrollments: Mapped[List["EnrollmentModel"]] = relationship("EnrollmentModel", back_populates="beneficiary", cascade="all, delete-orphan")
