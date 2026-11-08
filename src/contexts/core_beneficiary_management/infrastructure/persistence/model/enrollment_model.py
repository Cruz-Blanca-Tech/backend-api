import uuid
from datetime import date
from sqlalchemy import String, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.core.database import Base

class EnrollmentModel(Base):
    __tablename__ = "beneficiary_enrollments"
    # D21: un niño no puede quedar inscrito dos veces en la misma actividad,
    # aunque dos aprobaciones lleguen al mismo tiempo.
    __table_args__ = (
        UniqueConstraint("beneficiary_id", "activity_code", name="uq_enrollment_beneficiary_activity"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("beneficiaries.id"), nullable=False)
    activity_code: Mapped[str] = mapped_column(String(100), nullable=False)
    enrollment_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    beneficiary: Mapped["BeneficiaryModel"] = relationship("BeneficiaryModel", back_populates="enrollments")
