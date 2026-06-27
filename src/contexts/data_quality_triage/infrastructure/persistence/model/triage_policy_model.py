# src/contexts/data_quality_triage/infrastructure/persistence/models/triage_policy_model.py
from uuid import UUID, uuid4
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base

class TriagePolicyModel(Base):
    __tablename__ = "triage_policies"
    activity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    required_document_codes: Mapped[list] = mapped_column(JSON, nullable=False)