from abc import ABC, abstractmethod
from typing import Optional

from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary

class DossierProcessorStrategy(ABC):
    @abstractmethod
    def process(self, dossier_data: dict, existing_beneficiary: Optional[Beneficiary]) -> Beneficiary:
        """
        Process the raw dossier_data and update/create a Beneficiary domain entity.
        :param dossier_data: The raw JSON dictionary from the event.
        :param existing_beneficiary: The existing beneficiary from the DB, if any.
        :return: A fully constructed or updated Beneficiary entity.
        """
        pass
