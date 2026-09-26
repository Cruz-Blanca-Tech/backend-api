import asyncio
from src.core.database import engine, Base

# Import all models to register them with Base.metadata
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.education_record_model import EducationRecordModel
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.enrollment_model import EnrollmentModel
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.historical_document_model import HistoricalDocumentModel
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.medical_record_model import MedicalRecordModel
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.person_model import PersonModel
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.person_relationship_model import PersonRelationshipModel
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.adult_model import AdultModel
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.beneficiary_model import BeneficiaryModel
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.school_model import SchoolModel

from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_case_model import TriageCaseModel

from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_model import ActivityModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_requirement_model import ActivityRequirementModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model import DocumentItemModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.document_type_config import DocumentTypeConfigModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model import ExtractionBatchModel
from src.contexts.document_intake_ocr.infrastructure.persistence.model.program_model import ProgramModel

from src.contexts.security_access.infrastructure.persistence.models.refresh_token_model import RefreshTokenModel
from src.contexts.security_access.infrastructure.persistence.models.user_model import UserModel

from src.contexts.shared.infrastructure.persistence.model.failed_event_model import FailedEventModel

async def recreate():
    from sqlalchemy import text
    async with engine.begin() as conn:
        print("Dropping schema public cascade...")
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("Done!")

if __name__ == "__main__":
    asyncio.run(recreate())
