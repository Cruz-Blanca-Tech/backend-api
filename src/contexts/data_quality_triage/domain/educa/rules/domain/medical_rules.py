from typing import List
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DomainRule
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier

class MedicalRules(DomainRule):
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        # Los motivos de hospitalización y operación son opcionales: muchas veces
        # el padre marca "Sí" en la ficha FINS pero deja en blanco el motivo.
        return []
