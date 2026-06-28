from typing import Dict, Type
from src.contexts.data_quality_triage.domain.shared.strategies.base_strategy import TriageStrategy
from src.contexts.data_quality_triage.domain.shared.strategies.generic_strategy import GenericTriageStrategy

class TriageStrategyFactory:
    _strategies: Dict[str, Type[TriageStrategy]] = {}

    @classmethod
    def get_strategy(cls, document_codes: set, activity_id: str = None) -> TriageStrategy:
        from src.contexts.data_quality_triage.domain.shared.strategies.inscription_strategy import InscriptionTriageStrategy
        from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
        
        # Simulando mapeo de activity_id (UUID string) -> ActivityType
        # Temporalmente, forzamos EDUCA_INSCRIPTION. En producción, esto viene de una BD de config.
        activity_type = ActivityType.EDUCA_INSCRIPTION
        
        if activity_type == ActivityType.EDUCA_INSCRIPTION:
            return InscriptionTriageStrategy()
            
        return GenericTriageStrategy()
