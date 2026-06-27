import re
from typing import Dict, Any, List

from src.contexts.data_quality_triage.domain.shared.strategies.base_strategy import DossierValidationStrategy
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.value_objects.quality_rule_result import QualityRuleResult


DNI_PATTERN = re.compile(r"^\d{8}$")
PHONE_PATTERN = re.compile(r"^\d{9}$")


class InscriptionStrategy(DossierValidationStrategy):
    REQUIRED_FIELDS = [
        "child_dni", "child_first_name", "child_last_name", "child_birth_date",
    ]

    def validate(
        self,
        dossier_documents: Dict[str, Dict[str, Any]],
        confidence_scores: Dict[str, float],
        confidence_threshold: float,
    ) -> QualityRuleResult:
        discrepancies: List[FieldDiscrepancy] = []
        confidence_passed = True

        for doc_code, score in confidence_scores.items():
            if score is not None and score < confidence_threshold:
                confidence_passed = False
                discrepancies.append(FieldDiscrepancy(
                    field_name="confidence_score",
                    expected_pattern=f">= {confidence_threshold}",
                    actual_value=str(score),
                    rule_description=f"El score de confianza de {doc_code} ({score:.2f}) est? por debajo del umbral ({confidence_threshold})",
                    severity="WARNING",
                    document_code=doc_code,
                ))

        fins_data = dossier_documents.get("FINS", {})
        if fins_data:
            for field_name in self.REQUIRED_FIELDS:
                value = fins_data.get(field_name)
                if not value or (isinstance(value, str) and not value.strip()):
                    discrepancies.append(FieldDiscrepancy(
                        field_name=field_name,
                        expected_pattern="No vac?o",
                        actual_value=str(value) if value else "(vac?o)",
                        rule_description=f"El campo '{field_name}' es obligatorio",
                        severity="ERROR",
                        document_code="FINS",
                    ))

            child_dni = fins_data.get("child_dni", "")
            if child_dni and not DNI_PATTERN.match(str(child_dni)):
                discrepancies.append(FieldDiscrepancy(
                    field_name="child_dni",
                    expected_pattern="8 d?gitos num?ricos",
                    actual_value=str(child_dni),
                    rule_description=f"El DNI del ni?o '{child_dni}' no es v?lido",
                    severity="ERROR",
                    document_code="FINS",
                ))

            for dni_field in ["parents_father_dni", "parents_mother_dni", "parents_guardian_dni"]:
                dni_value = fins_data.get(dni_field)
                if dni_value and isinstance(dni_value, str) and dni_value.strip() and not DNI_PATTERN.match(dni_value):
                    discrepancies.append(FieldDiscrepancy(
                        field_name=dni_field,
                        expected_pattern="8 d?gitos num?ricos",
                        actual_value=dni_value,
                        rule_description=f"DNI '{dni_value}' no es v?lido",
                        severity="ERROR",
                        document_code="FINS",
                    ))

            child_gender = fins_data.get("child_gender")
            if child_gender and child_gender not in ("M", "F"):
                discrepancies.append(FieldDiscrepancy(
                    field_name="child_gender",
                    expected_pattern="M o F",
                    actual_value=str(child_gender),
                    rule_description=f"El g?nero '{child_gender}' no es v?lido",
                    severity="ERROR",
                    document_code="FINS",
                ))

        dj_data = dossier_documents.get("DJ", {})
        if fins_data and dj_data:
            fins_child_dni = str(fins_data.get("child_dni", "")).strip()
            dj_child_dni = str(dj_data.get("child_dni", dj_data.get("dni_nino", ""))).strip()
            
            if fins_child_dni and dj_child_dni and fins_child_dni != dj_child_dni:
                discrepancies.append(FieldDiscrepancy(
                    field_name="child_dni",
                    expected_pattern=f"Coincidir con DJ ({dj_child_dni})",
                    actual_value=f"FINS: {fins_child_dni}, DJ: {dj_child_dni}",
                    rule_description=f"El DNI del ni?o en FINS no coincide con DJ",
                    severity="ERROR",
                    document_code="FINS",
                ))

            fins_guardian_dnis = set()
            for dni_field in ["parents_father_dni", "parents_mother_dni", "parents_guardian_dni"]:
                v = fins_data.get(dni_field)
                if v and isinstance(v, str) and v.strip():
                    fins_guardian_dnis.add(v.strip())

            dj_guardian_dni = str(dj_data.get("guardian_dni", dj_data.get("dni_apoderado", ""))).strip()
            
            if dj_guardian_dni and fins_guardian_dnis and dj_guardian_dni not in fins_guardian_dnis:
                discrepancies.append(FieldDiscrepancy(
                    field_name="guardian_dni",
                    expected_pattern=f"Coincidir con FINS",
                    actual_value=f"DJ: {dj_guardian_dni}",
                    rule_description=f"El DNI del apoderado en DJ no coincide con los padres en FINS",
                    severity="ERROR",
                    document_code="DJ",
                ))

        has_errors = any(d.severity == "ERROR" for d in discrepancies)
        is_valid = not has_errors and confidence_passed

        return QualityRuleResult(
            is_valid=is_valid,
            discrepancies=discrepancies,
            confidence_passed=confidence_passed,
        )

    def get_field_definitions(self) -> List[dict]:
        return [
            {"name": "child_dni", "type": "text", "label": "DNI del Ni?o/a", "is_editable": True, "group": "datos_nino"},
            {"name": "child_first_name", "type": "text", "label": "Nombres", "is_editable": True, "group": "datos_nino"},
            {"name": "child_last_name", "type": "text", "label": "Apellidos", "is_editable": True, "group": "datos_nino"},
            {"name": "child_age", "type": "text", "label": "Edad", "is_editable": True, "group": "datos_nino"},
            {"name": "child_birth_date", "type": "date", "label": "Fecha de Nacimiento", "is_editable": True, "group": "datos_nino"},
            {"name": "child_gender", "type": "select", "label": "Sexo", "is_editable": True, "group": "datos_nino", "options": ["M", "F"]},
            {"name": "child_school", "type": "text", "label": "Colegio", "is_editable": True, "group": "datos_nino"},
            {"name": "child_grade", "type": "text", "label": "Grado", "is_editable": True, "group": "datos_nino"},

            {"name": "address_lot", "type": "text", "label": "Lote", "is_editable": True, "group": "direccion"},
            {"name": "address_block", "type": "text", "label": "Manzana", "is_editable": True, "group": "direccion"},
            {"name": "address_city", "type": "text", "label": "Ciudad", "is_editable": True, "group": "direccion"},
            {"name": "address_district", "type": "text", "label": "Distrito", "is_editable": True, "group": "direccion"},
            {"name": "address_neighborhood", "type": "text", "label": "Urbanizaci?n", "is_editable": True, "group": "direccion"},

            {"name": "parents_father_full_name", "type": "text", "label": "Padre", "is_editable": True, "group": "padres"},
            {"name": "parents_father_dni", "type": "text", "label": "DNI Padre", "is_editable": True, "group": "padres"},
            {"name": "parents_mother_full_name", "type": "text", "label": "Madre", "is_editable": True, "group": "padres"},
            {"name": "parents_mother_dni", "type": "text", "label": "DNI Madre", "is_editable": True, "group": "padres"},
            {"name": "parents_guardian_full_name", "type": "text", "label": "Apoderado", "is_editable": True, "group": "padres"},
            {"name": "parents_guardian_dni", "type": "text", "label": "DNI Apoderado", "is_editable": True, "group": "padres"},
        ]
