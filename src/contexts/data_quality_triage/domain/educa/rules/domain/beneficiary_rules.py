from typing import List
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DomainRule
from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier

class BeneficiaryCompletenessRule(DomainRule):
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        
        # Validar DNI
        dni = domain_entity.beneficiary.dni
        if not dni or not dni.strip():
            issues.append(FieldDiscrepancy(
                field_name="beneficiary.dni", expected_pattern="8 dígitos numéricos", actual_value="(vacío)",
                rule_description="El DNI del beneficiario es obligatorio.", severity="ERROR", document_code="DOMINIO"
            ))
        elif not (dni.isdigit() and len(dni) == 8):
            issues.append(FieldDiscrepancy(
                field_name="beneficiary.dni", expected_pattern="8 dígitos numéricos", actual_value=str(dni),
                rule_description="El DNI del beneficiario debe tener exactamente 8 dígitos numéricos.", severity="ERROR", document_code="DOMINIO"
            ))

        if not domain_entity.beneficiary.first_name or not domain_entity.beneficiary.last_name:
            issues.append(FieldDiscrepancy(
                field_name="beneficiary.name", expected_pattern="Nombre y Apellido", actual_value="(vacío)",
                rule_description="El nombre y apellido del beneficiario son obligatorios.", severity="ERROR", document_code="DOMINIO"
            ))

        if not domain_entity.beneficiary.birth_date:
            issues.append(FieldDiscrepancy(
                field_name="beneficiary.birth_date", expected_pattern="Fecha válida (YYYY-MM-DD)", actual_value="(vacío)",
                rule_description="La fecha de nacimiento del beneficiario es un campo obligatorio.", severity="ERROR", document_code="DOMINIO"
            ))
        if not domain_entity.beneficiary.gender:
            issues.append(FieldDiscrepancy(
                field_name="beneficiary.gender", expected_pattern="M o F", actual_value="(vacío)",
                rule_description="El sexo del beneficiario es un campo obligatorio.", severity="ERROR", document_code="DOMINIO"
            ))
        return issues

class AgeCoherenceRule(DomainRule):
    """
    Valida que la edad calculada no supere la edad máxima razonable para un niño.
    Solo marca error si la edad calculada excede MAX_CHILD_AGE (18 años).
    No valida coherencia con la edad proporcionada (puede haber errores de OCR).
    """
    MAX_CHILD_AGE = 18
    
    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        if domain_entity.beneficiary.birth_date:
            try:
                from datetime import datetime
                birth_date = datetime.strptime(domain_entity.beneficiary.birth_date.split("T")[0], "%Y-%m-%d")
                current_year = datetime.now().year
                calculated_age = current_year - birth_date.year
                if calculated_age > self.MAX_CHILD_AGE:
                    issues.append(FieldDiscrepancy(
                        field_name="beneficiary.birth_date", expected_pattern=f"Edad <= {self.MAX_CHILD_AGE} años", 
                        actual_value=f"{calculated_age} años",
                        rule_description=f"La fecha de nacimiento indica una edad de {calculated_age} años, que excede la edad máxima para un niño ({self.MAX_CHILD_AGE} años). Verifique la fecha de nacimiento.", 
                        severity="ERROR", document_code="DOMINIO"
                    ))
            except Exception:
                pass
        return issues

class GenderCoherenceRule(DomainRule):
    """Valida que el sexo del beneficiario sea uno de los valores reconocidos.

    Cuando el OCR no logra leer el sexo deja el centinela `UNKNOWN`
    (ver `GenderNormalizer`). Para el operador ese centinela no significa nada:
    no es un valor que pueda corregir, es la ausencia del dato. Por eso NO se
    reporta como un valor recibido inválido, sino como un dato que no llegó.
    """

    # Centinelas que el normalizador/OCR dejan cuando no leyeron el sexo.
    SEXO_NO_RECIBIDO = ("UNKNOWN", "UNKNOW", "NO_LEIDO", "SIN_DATO")

    def evaluate(self, domain_entity: EducaInscriptionDossier) -> List[FieldDiscrepancy]:
        issues = []
        if domain_entity.beneficiary.gender:
            # El maestro serializa el enum (`MALE`/`FEMALE`) y el OCR/FINS usa
            # `M`/`F`: ambos son válidos. Solo se marca error si el valor no es
            # ninguno de los sinónimos reconocidos (p. ej. ruido de OCR).
            gender = domain_entity.beneficiary.gender.strip().upper()
            if gender not in ("M", "F", "MALE", "FEMALE"):
                if gender in self.SEXO_NO_RECIBIDO:
                    valor_leido = "(no se ha recibido)"
                    descripcion = (
                        "No se ha recibido el sexo del beneficiario: la IA no pudo "
                        "leerlo en los documentos. Revisá las imágenes y elegí "
                        "Masculino o Femenino."
                    )
                else:
                    valor_leido = "(ilegible)"
                    descripcion = (
                        "El sexo del beneficiario se leyó como un texto que no se "
                        "reconoce. Revisá las imágenes y elegí Masculino o Femenino."
                    )
                issues.append(FieldDiscrepancy(
                    field_name="beneficiary.gender",
                    expected_pattern="Masculino o Femenino",
                    actual_value=valor_leido,
                    rule_description=descripcion,
                    severity="ERROR", document_code="DOMINIO"
                ))
        return issues
