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
        
        msg_format = "Atención: El número de DNI que la IA logró leer en este documento parece estar incompleto o tener caracteres extraños. Por favor, dale un vistazo a la imagen y corrígelo si es necesario."
        
        if enriched_fins:
            dnis_to_evaluate.append((enriched_fins.child_dni, f"Ficha FINS (Niño): {msg_format}", EducaDocumentCode.FINS.value))
            dnis_to_evaluate.extend([
                (adult.dni, f"Ficha FINS (Adulto - {adult.role}): {msg_format}", EducaDocumentCode.FINS.value) 
                for adult in enriched_fins.adults
            ])
            
        if enriched_dj:
            dnis_to_evaluate.append((enriched_dj.child_dni, f"DJ (Niño): {msg_format}", EducaDocumentCode.DJ.value))
            dnis_to_evaluate.append((enriched_dj.guardian_dni, f"DJ (Apoderado): {msg_format}", EducaDocumentCode.DJ.value))
            
        if enriched_dnibe:
            dnis_to_evaluate.append((enriched_dnibe.document_number, f"Copia de DNI (Niño): {msg_format}", "DNIBE"))
            
        if enriched_dniap:
            dnis_to_evaluate.append((enriched_dniap.document_number, f"Copia de DNI (Apoderado): {msg_format}", "DNIAP"))

        for dni_field, error_msg, doc_code in dnis_to_evaluate:
            # Si el campo tiene un error de formato (ej. no es válido)
            if not dni_field.is_valid:
                discrepancies.append(FieldDiscrepancy(
                    field_name=dni_field.name, expected_pattern="DNI de 8 dígitos", 
                    actual_value=str(dni_field.raw_value),
                    rule_description=error_msg, 
                    severity="WARNING", document_code=doc_code
                ))
        return discrepancies

def _edit_distance(a: str, b: str) -> int:
    """Distancia de Levenshtein entre dos cadenas (mínimo de ediciones de 1 carácter).

    Se usa para distinguir en el DNI del niño:
      - diferencia de UN dígito (posible error de OCR/localéase de teclado);
      - diferencia de VARIOS dígitos (dos números distintos de verdad).
    """
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cur.append(min(
                prev[j] + 1,
                cur[-1] + 1,
                prev[j - 1] + (ca != cb),
            ))
        prev = cur
    return prev[-1]


_DOC_LABELS = {
    EducaDocumentCode.FINS.value: "la ficha de inscripción (FINS)",
    EducaDocumentCode.DJ.value: "la declaración jurada (DJ)",
    EducaDocumentCode.DNI_BENEFICIARY.value: "la copia del DNI del niño",
    EducaDocumentCode.DNI_APODERADO.value: "la copia del DNI del apoderado",
    EducaDocumentCode.DNI_GENERIC.value: "la copia del DNI",
}


def _document_labels(codes) -> str:
    """Nombres amigables de los documentos en un mensaje al operador."""
    labels = [_DOC_LABELS.get(c, c) for c in codes]
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " y " + labels[-1]


class BeneficiaryDniCrosscheckRule(DocumentRule):
    """Cruza los DNIs del beneficiario (niño) entre los documentos presentados.

    Implementa la tabla de decisión acordada con el operador:
      1) Todas las lecturas válidas coinciden              → touchless (nada que hacer).
      2) La FINS no aporta un DNI válido pero 2+ documentos
         válidos coinciden                                 → AI_INSIGHT "corroborado":
         se sugiere el DNI para confirmar en un clic.
      3) Las lecturas válidas difieren por 1 dígito        → proponer el mayoritario
         (AI_INSIGHT) + advertencia visible; NUNCA auto-cerrar.
      4) Difieren por varios dígitos                       → ERROR, lo resuelve el operador.
      5) Ningún documento con DNI válido                   → nada aquí: el ERROR de
         completitud ("El DNI del beneficiario es obligatorio") pide cargarlo a mano.
    """

    # Convención interna: marca las sugerencias de DNI corroborado por documentos
    # para que el procesador pueda tomar la decisión touchless contra el maestro
    # (caso 6: DNI existe en el maestro y calza nombre + fecha de nacimiento).
    CORROBORATION_DOC = "CORROBORATED"

    def evaluate(self, enriched_fins: Any = None, enriched_dj: Any = None, enriched_dnibe: Any = None, **kwargs) -> List[FieldDiscrepancy]:
        readings = {}
        if enriched_fins:
            readings[EducaDocumentCode.FINS.value] = enriched_fins.child_dni
        if enriched_dj:
            readings[EducaDocumentCode.DJ.value] = enriched_dj.child_dni
        if enriched_dnibe:
            readings[EducaDocumentCode.DNI_BENEFICIARY.value] = enriched_dnibe.document_number

        valid = {
            doc: str(field.normalized_value)
            for doc, field in readings.items()
            if field and field.is_valid and field.normalized_value
        }

        # Caso 5 (o sin cruce posible): con menos de 2 lecturas no hay
        # corroboración entre documentos; las reglas de completitud ya avisan.
        if len(valid) < 2:
            return []

        values = list(valid.values())

        # Caso 1: todas las lecturas válidas coinciden → touchless.
        if len(set(values)) == 1:
            value = values[0]
            # Si la FINS aporta el DNI, ya vive en el expediente: nada que hacer.
            if EducaDocumentCode.FINS.value in valid:
                return []
            # Caso 2: FINS sin DNI válido, pero 2+ documentos coinciden.
            sources = _document_labels([d for d in valid if d != EducaDocumentCode.FINS.value])
            return [FieldDiscrepancy(
                field_name="beneficiary.dni",
                expected_pattern=value,
                actual_value="(vacío)",
                rule_description=(
                    f"La ficha FINS no trae un DNI legible para el niño, pero la IA "
                    f"leyó el DNI {value} en {sources}. Si coincide con los documentos, "
                    f"aplicá con un clic para completar el DNI. Si no, escribí el número correcto."
                ),
                severity="AI_INSIGHT",
                document_code=self.CORROBORATION_DOC,
            )]

        # Casos 3 y 4: las lecturas válidas NO coinciden entre sí.
        from collections import Counter
        mismatch = ", ".join(f"{d}: {v}" for d, v in sorted(valid.items()))
        pairwise = [
            _edit_distance(a, b)
            for i, a in enumerate(values)
            for b in values[i + 1:]
        ]
        # ¿Todo el conjunto difiere como máximo en 1 dígito? → caso 3 (fuzzy).
        fuzzy_by_one = bool(pairwise) and max(pairwise) <= 1
        majority, majority_count = Counter(values).most_common(1)[0]

        if fuzzy_by_one:
            # Advertencia visible SIEMPRE que las lecturas difieran en 1 dígito:
            # en un DNI, una cifra distinta puede ser otra persona real. La
            # propuesta del mayoritario es solo para agilizar al operador.
            out = [FieldDiscrepancy(
                field_name="beneficiary_dni_crosscheck",
                expected_pattern="DNI único para el niño",
                actual_value=mismatch,
                rule_description=(
                    "Atención: la IA leyó el DNI del niño con un dígito de diferencia "
                    f"entre los documentos ({mismatch}). Una cifra distinta puede ser "
                    "otra persona: revisá las imágenes y confirmá cuál número es el correcto."
                ),
                severity="WARNING",
                document_code="CROSS_CHECK",
            )]
            if majority_count > 1:
                out.append(FieldDiscrepancy(
                    field_name="beneficiary.dni",
                    expected_pattern=majority,
                    actual_value=mismatch,
                    rule_description=(
                        f"La mayoría de los documentos leyeron el DNI {majority} para el "
                        f"niño (los demás difieren en una cifra). No se aplicó solo: verificá "
                        f"las imágenes y usá el botón para aplicarlo si es el correcto."
                    ),
                    severity="AI_INSIGHT",
                    document_code=self.CORROBORATION_DOC,
                ))
            return out

        # Caso 4: lecturas válidas que difieren en varios dígitos → ERROR.
        return [FieldDiscrepancy(
            field_name="beneficiary_dni_crosscheck",
            expected_pattern="DNI único para el niño",
            actual_value=mismatch,
            rule_description=(
                f"Atención: la IA leyó DNIs muy distintos para el niño en los documentos "
                f"({mismatch}). Revisá las imágenes y escribí el número correcto."
            ),
            severity="ERROR",
            document_code="CROSS_CHECK",
        )]

class GuardianDniCrosscheckRule(DocumentRule):
    """Cruza los DNIs del apoderado entre DJ, DNIAP y los adultos del FINS."""
    def evaluate(self, enriched_fins: Any = None, enriched_dj: Any = None, enriched_dniap: Any = None, **kwargs) -> List[FieldDiscrepancy]:
        discrepancies = []
        
        # 1. Cruzar DNIAP vs DJ (deben ser exactamente iguales si existen)
        dnis_to_check_exact = []
        if enriched_dj:
            dnis_to_check_exact.append((EducaDocumentCode.DJ.value, enriched_dj.guardian_dni))
        if enriched_dniap:
            dnis_to_check_exact.append((EducaDocumentCode.DNI_APODERADO.value, enriched_dniap.document_number))
            
        discrepancies.extend(validate_exact_match(
            dnis_to_check_exact, 
            field_name="guardian_dni_crosscheck_exact", 
            rule_description="Atención: El DNI del apoderado que se leyó en la DJ no coincide con el número extraído de su copia de identidad (DNIAP). Verifica cuál de los dos leyó mal la IA."
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
                    expected_pattern=f"DNI asociado: {adult_dnis}",
                    actual_value=dj_guardian_val,
                    rule_description="Atención: El DNI del apoderado en la DJ no coincide con el de los padres mencionados en la ficha FINS. Échale un vistazo para ver si la IA se confundió al leer algún número.", 
                    severity="WARNING", 
                    document_code="CROSS_CHECK"
                ))
                
        return discrepancies
