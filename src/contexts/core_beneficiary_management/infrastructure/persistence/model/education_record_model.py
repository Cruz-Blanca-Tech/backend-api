import uuid
from sqlalchemy import Boolean, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.core.database import Base

class EducationRecordModel(Base):
    __tablename__ = "education_records"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("beneficiaries.id"), unique=True)

    school: Mapped[str] = mapped_column(String(200), nullable=True)
    grade: Mapped[str] = mapped_column(String(100), nullable=True)
    knows_how_to_read: Mapped[bool] = mapped_column(Boolean, default=False)
    knows_how_to_write: Mapped[bool] = mapped_column(Boolean, default=False)
    has_repeated_grade: Mapped[bool] = mapped_column(Boolean, default=False)
    has_learning_difficulties: Mapped[bool] = mapped_column(Boolean, default=False)

    beneficiary = relationship("BeneficiaryModel", back_populates="education_record")
