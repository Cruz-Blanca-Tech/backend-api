from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple

from src.contexts.data_quality_triage.domain.shared.utils.string_utils import calculate_similarity
from src.contexts.data_quality_triage.domain.shared.value_objects.dossier_data import DossierData
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData
from src.contexts.data_quality_triage.domain.educa.value_objects.medical_data import MedicalData


@dataclass
class EducaInscription(DossierData):
    beneficiary: BeneficiaryData
    related_adults: FamilyData
    education: EducationData
    medical: MedicalData


    def validate_completeness(self) -> Tuple[bool, List[FieldDiscrepancy]]:
        """Valida que el dossier esté completo orquestando DomainRules."""
        from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
        
        # Importamos las reglas ultra-modulares
        from src.contexts.data_quality_triage.domain.educa.rules.domain.beneficiary_rules import BeneficiaryCompletenessRule, AgeCoherenceRule
        from src.contexts.data_quality_triage.domain.educa.rules.domain.family_rules import GuardianPresenceRule, EmergencyContactRule
        from src.contexts.data_quality_triage.domain.educa.rules.domain.medical_rules import MedicalRules
        from src.contexts.data_quality_triage.domain.educa.rules.domain.education_rules import EducationRules
        
        issues: List[FieldDiscrepancy] = []

        rules = [
            BeneficiaryCompletenessRule(),
            AgeCoherenceRule(),
            EmergencyContactRule(),
            GuardianPresenceRule(),
            MedicalRules(),
            EducationRules()
        ]
        
        for rule in rules:
            issues.extend(rule.evaluate(self))

        self.beneficiary.validation_issues = [i.rule_description for i in issues if "beneficiary" in i.field_name]
        self.related_adults.validation_issues = [i.rule_description for i in issues if "related_adults" in i.field_name]
        
        is_valid = len(issues) == 0
        return is_valid, issues
