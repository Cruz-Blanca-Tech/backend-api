import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.contexts.core_beneficiary_management.infrastructure.persistence.model.person_model import PersonModel
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.person_relationship_model import PersonRelationshipModel

class AdultModel(PersonModel):
    __tablename__ = "adults"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), primary_key=True)
    
    role: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    is_emergency_contact: Mapped[bool] = mapped_column(default=False)
    is_guardian: Mapped[bool] = mapped_column(default=False)

    __mapper_args__ = {
        "polymorphic_identity": "adult",
    }

    beneficiaries = relationship(
        "BeneficiaryModel",
        secondary="person_relationships",
        primaryjoin="AdultModel.id == foreign(PersonRelationshipModel.to_person_id)",
        secondaryjoin="BeneficiaryModel.id == foreign(PersonRelationshipModel.from_person_id)",
        back_populates="relatives"
    )
