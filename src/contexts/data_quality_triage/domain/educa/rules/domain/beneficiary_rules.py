from typing import List
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DomainRule
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier

class BeneficiaryCompletenessRule(DomainRule):
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        if not domain_entity.beneficiary.first_name or not domain_entity.beneficiary.last_name:
            issues.append(FieldDiscrepancy(
                field_name="beneficiary.name", expected_pattern="Nombre y Apellido", actual_value="(vacío)",
                rule_description="El nombre y apellido del beneficiario son obligatorios.", severity="ERROR", document_code="DOMINIO"
            ))
        if not domain_entity.beneficiary.gender:
            issues.append(FieldDiscrepancy(
                field_name="beneficiary.gender", expected_pattern="M o F", actual_value="(vacío)",
                rule_description="El sexo del beneficiario es un campo obligatorio.", severity="ERROR", document_code="DOMINIO"
            ))
        return issues

class AgeCoherenceRule(DomainRule):
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        if domain_entity.beneficiary.birth_date and domain_entity.beneficiary.age is not None:
            try:
                from datetime import datetime
                birth_date = datetime.strptime(domain_entity.beneficiary.birth_date.split("T")[0], "%Y-%m-%d")
                current_year = datetime.now().year
                calculated_age = current_year - birth_date.year
                if abs(calculated_age - int(domain_entity.beneficiary.age)) > 1:
                    issues.append(FieldDiscrepancy(
                        field_name="beneficiary.age", expected_pattern="Coherencia con fecha de nacimiento", 
                        actual_value=str(domain_entity.beneficiary.age),
                        rule_description=f"La edad proporcionada no coincide lógicamente con la fecha de nacimiento ({domain_entity.beneficiary.birth_date}).", 
                        severity="ERROR", document_code="DOMINIO"
                    ))
            except Exception:
                pass
        return issues

class GenderCoherenceRule(DomainRule):
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        if domain_entity.beneficiary.gender:
            if domain_entity.beneficiary.gender not in ["M", "F"]:
                issues.append(FieldDiscrepancy(
                    field_name="beneficiary.gender", expected_pattern="M o F", 
                    actual_value=str(domain_entity.beneficiary.gender),
                    rule_description=f"El sexo debe ser 'M' (Masculino) o 'F' (Femenino). Valor recibido: {domain_entity.beneficiary.gender}", 
                    severity="ERROR", document_code="DOMINIO"
                ))
        return issues
