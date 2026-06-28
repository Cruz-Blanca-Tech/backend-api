from typing import List, Any
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.rules.base_rule import DocumentRule
from src.contexts.data_quality_triage.domain.educa.value_objects.document_code import EducaDocumentCode
from src.contexts.data_quality_triage.domain.shared.rules.crosscheck_utils import validate_exact_match

class DniFormatRule(DocumentRule):
    """Valida que los DNIs encontrados hayan podido ser normalizados correctamente (lo que implica que son válidos)."""
    def evaluate(self, enriched_fins: Any = None, enriched_dj: Any = None, enriched_dnibe: Any = None, enriched_dniap: Any = None, **kwargs) -> List[FieldDiscrepancy]:
        discrepancies = []
        dnis_to_evaluate = []
        
        if enriched_fins:
            dnis_to_evaluate.append((enriched_fins.child_dni, "El DNI del niño escaneado en FINS no tiene un formato válido", EducaDocumentCode.FINS.value))
            dnis_to_evaluate.extend([
                (adult.dni, f"DNI de adulto escaneado ({adult.role}) no es válido", EducaDocumentCode.FINS.value) 
                for adult in enriched_fins.adults
            ])
            
        if enriched_dj:
            dnis_to_evaluate.append((enriched_dj.child_dni, "El DNI del niño en DJ no tiene un formato válido", EducaDocumentCode.DJ.value))
            dnis_to_evaluate.append((enriched_dj.guardian_dni, "El DNI del apoderado en DJ no tiene un formato válido", EducaDocumentCode.DJ.value))
            
        if enriched_dnibe:
            dnis_to_evaluate.append((enriched_dnibe.dni_number, "El documento DNI del beneficiario no es válido", "DNIBE"))
            
        if enriched_dniap:
            dnis_to_evaluate.append((enriched_dniap.dni_number, "El documento DNI del apoderado no es válido", "DNIAP"))

        for dni_field, error_msg, doc_code in dnis_to_evaluate:
            # Si el campo tiene un error de formato (ej. no es válido)
            if not dni_field.is_valid:
                discrepancies.append(FieldDiscrepancy(
                    field_name=dni_field.name, expected_pattern="Formato de DNI válido", 
                    actual_value=str(dni_field.raw_value),
                    rule_description=error_msg, 
                    severity="ERROR", document_code=doc_code
                ))
        return discrepancies

class BeneficiaryDniCrosscheckRule(DocumentRule):
    """Cruza los DNIs del beneficiario (niño) entre los distintos documentos presentados."""
    def evaluate(self, enriched_fins: Any = None, enriched_dj: Any = None, enriched_dnibe: Any = None, **kwargs) -> List[FieldDiscrepancy]:
        dnis_to_check = []
        if enriched_fins:
            dnis_to_check.append((EducaDocumentCode.FINS.value, enriched_fins.child_dni))
        if enriched_dj:
            dnis_to_check.append((EducaDocumentCode.DJ.value, enriched_dj.child_dni))
        if enriched_dnibe:
            dnis_to_check.append((EducaDocumentCode.DNI_BENEFICIARY.value, enriched_dnibe.dni_number))
            
        return validate_exact_match(
            dnis_to_check, 
            field_name="beneficiary_dni_crosscheck", 
            rule_description="Existe una discrepancia de DNI del beneficiario entre los documentos presentados."
        )

class GuardianDniCrosscheckRule(DocumentRule):
    """Cruza los DNIs del apoderado entre DJ, DNIAP y los adultos del FINS."""
    def evaluate(self, enriched_fins: Any = None, enriched_dj: Any = None, enriched_dniap: Any = None, **kwargs) -> List[FieldDiscrepancy]:
        discrepancies = []
        
        # 1. Cruzar DNIAP vs DJ (deben ser exactamente iguales si existen)
        dnis_to_check_exact = []
        if enriched_dj:
            dnis_to_check_exact.append((EducaDocumentCode.DJ.value, enriched_dj.guardian_dni))
        if enriched_dniap:
            dnis_to_check_exact.append((EducaDocumentCode.DNI_APODERADO.value, enriched_dniap.dni_number))
            
        discrepancies.extend(validate_exact_match(
            dnis_to_check_exact, 
            field_name="guardian_dni_crosscheck_exact", 
            rule_description="El DNI del apoderado en la DJ no coincide con el documento DNIAP."
        ))

        # 2. Verificar que el apoderado (de DJ o DNIAP) esté en el FINS
        dj_guardian_val = None
        if enriched_dj and enriched_dj.guardian_dni.is_valid and enriched_dj.guardian_dni.normalized_value:
            dj_guardian_val = str(enriched_dj.guardian_dni.normalized_value)
            
        if dj_guardian_val and enriched_fins and enriched_fins.adults:
            adult_dnis = [str(a.dni.normalized_value) for a in enriched_fins.adults if a.dni.is_valid and a.dni.normalized_value]
            
            if adult_dnis and dj_guardian_val not in adult_dnis:
                discrepancies.append(FieldDiscrepancy(
                    field_name="guardian_dni_crosscheck_fins", 
                    expected_pattern=f"Coincidir con adultos de FINS: {adult_dnis}",
                    actual_value=dj_guardian_val,
                    rule_description="El DNI del declarante en la DJ no coincide con ninguno de los padres/apoderados declarados en la ficha FINS.", 
                    severity="WARNING", 
                    document_code="CROSS_CHECK"
                ))
                
        return discrepancies
