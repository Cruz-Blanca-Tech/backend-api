from sqlalchemy import Column, String, Date, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, UUID as PG_UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from src.core.database.session import Base
import uuid
from datetime import date

class BeneficiaryModel(Base):
    __tablename__ = "beneficiaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dni: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    birth_date: Mapped[Date] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(String(1))

    medical_record = relationship("MedicalRecordModel", back_populates="beneficiary", uselist=False, cascade="all, delete-orphan")
    education_record = relationship("EducationRecordModel", back_populates="beneficiary", uselist=False, cascade="all, delete-orphan")
    relatives = relationship("RelativeModel", back_populates="beneficiary", cascade="all, delete-orphan")
    historical_documents: Mapped[List["HistoricalDocumentModel"]] = relationship(back_populates="beneficiary", cascade="all, delete-orphan")
    enrollments: Mapped[List["EnrollmentModel"]] = relationship(back_populates="beneficiary", cascade="all, delete-orphan")


class MedicalRecordModel(Base):
    __tablename__ = "medical_records"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("beneficiaries.id"), unique=True)
    
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


class EducationRecordModel(Base):
    __tablename__ = "education_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("beneficiaries.id"), unique=True)

    school: Mapped[str] = mapped_column(String(200), nullable=True)
    grade: Mapped[str] = mapped_column(String(100), nullable=True)
    knows_how_to_read: Mapped[bool] = mapped_column(Boolean, default=False)
    knows_how_to_write: Mapped[bool] = mapped_column(Boolean, default=False)
    has_repeated_grade: Mapped[bool] = mapped_column(Boolean, default=False)
    has_learning_difficulties: Mapped[bool] = mapped_column(Boolean, default=False)

    beneficiary = relationship("BeneficiaryModel", back_populates="education_record")


class RelativeModel(Base):
    __tablename__ = "relatives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("beneficiaries.id"))

    dni: Mapped[str] = mapped_column(String(20))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(50), nullable=True)

    beneficiary = relationship("BeneficiaryModel", back_populates="relatives")


class EnrollmentModel(Base):
    __tablename__ = "beneficiary_enrollments"
    
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("beneficiaries.id"), nullable=False)
    activity_code: Mapped[str] = mapped_column(String(100), nullable=False)
    enrollment_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    beneficiary: Mapped["BeneficiaryModel"] = relationship(back_populates="enrollments")

class HistoricalDocumentModel(Base):
    __tablename__ = "historical_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("beneficiaries.id"))

    document_type: Mapped[str] = mapped_column(String(100))
    year: Mapped[int] = mapped_column()
    file_url: Mapped[str] = mapped_column(String(1000))

    beneficiary = relationship("BeneficiaryModel", back_populates="historical_documents")
