import uuid
from src.contexts.shared.events.dossier_pdf_generated_event import DossierPdfGeneratedEvent
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.domain.value_objects.historical_document import HistoricalDocument

class SaveHistoricalDocumentUseCase:
    """
    Listens to DossierPdfGeneratedEvent from OCR/Document module and appends
    the generated PDF to the beneficiary's historical documents.
    """
    def __init__(self, beneficiary_repo: SqlBeneficiaryRepository):
        self.beneficiary_repo = beneficiary_repo

    async def execute(self, event: DossierPdfGeneratedEvent):
        # 1. Fetch beneficiary by the real corrected DNI
        beneficiary = await self.beneficiary_repo.get_by_dni(event.dni)
        if not beneficiary:
            print(f"Warning: Beneficiary with DNI {event.dni} not found when saving historical document.")
            return

        # 2. Create the HistoricalDocument Value Object
        doc = HistoricalDocument(
            id=uuid.uuid4(),
            beneficiary_id=beneficiary.id,
            batch_id=event.batch_id,
            document_type=event.document_type,
            year=event.year,
            file_url=event.file_url
        )

        # 3. Append to beneficiary
        beneficiary.historical_documents.append(doc)

        # 4. Save beneficiary
        await self.beneficiary_repo.save(beneficiary)
