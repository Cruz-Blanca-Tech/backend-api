import uuid
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.core.database import Base

class HistoricalDocumentModel(Base):
    __tablename__ = "historical_documents"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("beneficiaries.id"))
    batch_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    document_type: Mapped[str] = mapped_column(String(100))
    year: Mapped[int] = mapped_column(Integer)
    file_url: Mapped[str] = mapped_column(String(1000))

    beneficiary = relationship("BeneficiaryModel", back_populates="historical_documents")
