from typing import Dict, Type
from src.contexts.data_quality_triage.domain.shared.strategies.base_strategy import TriageStrategy
from src.contexts.data_quality_triage.domain.shared.strategies.generic_strategy import GenericTriageStrategy

class TriageStrategyFactory:
    _strategies: Dict[str, Type[TriageStrategy]] = {}

    @classmethod
    def get_strategy(cls, document_codes: set, activity_type_str: str = None) -> TriageStrategy:
        from src.contexts.data_quality_triage.domain.shared.strategies.inscription_strategy import InscriptionTriageStrategy
        from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
        
        try:
            activity_type = ActivityType(activity_type_str) if activity_type_str else None
        except ValueError:
            activity_type = None
        
        if activity_type == ActivityType.EDUCA_INSCRIPTION:
            return InscriptionTriageStrategy()
            
        return GenericTriageStrategy()
