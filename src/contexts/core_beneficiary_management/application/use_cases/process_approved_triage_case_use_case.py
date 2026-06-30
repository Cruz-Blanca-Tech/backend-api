from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.application.shared.factories.dossier_processor_factory import DossierProcessorFactory

class ProcessApprovedTriageCaseUseCase:
    """
    Orchestrates the processing of an approved triage dossier by delegating 
    to the appropriate strategy based on the activity_type.
    """
    def __init__(self, beneficiary_repo: SqlBeneficiaryRepository):
        self.beneficiary_repo = beneficiary_repo

    async def execute(self, event: DossierApprovedEvent):
        # 1. Basic validation
        data = event.dossier_data
        dni = data.get("beneficiary", {}).get("dni")
        if not dni:
            # We must have a DNI to process any beneficiary
            return
            
        # 2. Get existing beneficiary if any
        existing_beneficiary = await self.beneficiary_repo.get_by_dni(dni)
        
        # 3. Get the correct strategy processor for this program (e.g. "EDUCA")
        try:
            processor = DossierProcessorFactory.get_processor(event.activity_type)
        except ValueError as e:
            # Log error or handle unsupported activity types
            print(f"Warning: {e}")
            return
            
        # 4. Delegate the heavy lifting to the specific processor (DTO validation, Mapping, etc.)
        updated_beneficiary = processor.process(data, existing_beneficiary)

        # 5. Persist the updated/new domain entity
        await self.beneficiary_repo.save(updated_beneficiary)
