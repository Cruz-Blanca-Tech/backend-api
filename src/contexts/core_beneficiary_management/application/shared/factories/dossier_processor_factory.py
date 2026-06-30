from src.contexts.core_beneficiary_management.application.shared.ports.dossier_processor_strategy import DossierProcessorStrategy
from src.contexts.core_beneficiary_management.application.use_cases.strategies.educa_dossier_processor import EducaDossierProcessor

class DossierProcessorFactory:
    @staticmethod
    def get_processor(activity_type: str) -> DossierProcessorStrategy:
        activity_type = activity_type.upper()
        if activity_type in ("EDUCA", "EDUCA_INSCRIPTION"):
            return EducaDossierProcessor()
        
        # You can add more programs here in the future
        # elif activity_type == "SALUD":
        #     return SaludDossierProcessor()
            
        raise ValueError(f"No processor strategy found for activity type: {activity_type}")
