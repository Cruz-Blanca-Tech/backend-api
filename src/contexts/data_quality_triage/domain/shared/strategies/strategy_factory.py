from typing import Dict, Type
from src.contexts.data_quality_triage.domain.shared.strategies.base_strategy import DossierValidationStrategy
from src.contexts.data_quality_triage.domain.shared.strategies.generic_strategy import GenericStrategy

class DossierStrategyFactory:
    _strategies: Dict[str, Type[DossierValidationStrategy]] = {}

    @classmethod
    def get_strategy(cls, activity_type: str) -> DossierValidationStrategy:
        strategy_class = cls._strategies.get(activity_type, GenericStrategy)
        return strategy_class()

    @classmethod
    def register_strategy(cls, activity_type: str, strategy_class: Type[DossierValidationStrategy]) -> None:
        cls._strategies[activity_type] = strategy_class

    @classmethod
    def get_strategy_for_documents(cls, document_codes: set) -> DossierValidationStrategy:
        from src.contexts.data_quality_triage.domain.shared.strategies.inscription_strategy import InscriptionStrategy
        if "FINS" in document_codes:
            return InscriptionStrategy()
        return GenericStrategy()
