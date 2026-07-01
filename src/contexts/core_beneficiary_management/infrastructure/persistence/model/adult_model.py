import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.contexts.core_beneficiary_management.infrastructure.persistence.model.person_model import PersonModel

class AdultModel(PersonModel):
    __tablename__ = "adults"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("persons.id"), primary_key=True)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("beneficiaries.id"), nullable=True)
    
    role: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    is_emergency_contact: Mapped[bool] = mapped_column(default=False)

    __mapper_args__ = {
        "polymorphic_identity": "adult",
    }

    beneficiary = relationship("BeneficiaryModel", back_populates="relatives", foreign_keys=[beneficiary_id])
