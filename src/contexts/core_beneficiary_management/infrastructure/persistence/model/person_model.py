import uuid
from datetime import date
from sqlalchemy import String, Date
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

class PersonModel(Base):
    __tablename__ = "persons"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dni: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    birth_date: Mapped[date] = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(String(1), nullable=True)
    
    # Polymorphic type column
    type: Mapped[str] = mapped_column(String(50))

    __mapper_args__ = {
        "polymorphic_identity": "person",
        "polymorphic_on": type,
    }
