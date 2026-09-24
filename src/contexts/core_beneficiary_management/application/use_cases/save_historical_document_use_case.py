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

        # 2. Search for existing historical document for the same document_type and year
        existing_doc = next((d for d in beneficiary.historical_documents if d.document_type == event.document_type and d.year == event.year), None)
        
        if existing_doc:
            beneficiary.historical_documents.remove(existing_doc)

        # 3. Create the HistoricalDocument Value Object
        doc = HistoricalDocument(
            id=existing_doc.id if existing_doc else uuid.uuid4(),
            beneficiary_id=beneficiary.id,
            batch_id=event.batch_id,
            document_type=event.document_type,
            year=event.year,
            file_id=event.file_id
        )

        # 4. Append to beneficiary
        beneficiary.historical_documents.append(doc)

        # 5. Save beneficiary
        await self.beneficiary_repo.save(beneficiary)
