from typing import Dict, Any, List
from src.contexts.data_quality_triage.domain.shared.services.dossier_policy import DossierPolicy
from src.contexts.data_quality_triage.application.educa.dtos.raw.fins_raw import FinsRaw
from src.contexts.data_quality_triage.application.educa.dtos.raw.dj_raw import DjRaw
from src.contexts.data_quality_triage.application.educa.dtos.raw.dni_raw import DniRaw

from src.contexts.data_quality_triage.domain.educa.value_objects.document_code import EducaDocumentCode

class EducaInscriptionPolicy(DossierPolicy):
    """
    Política específica para la actividad Educa Inscription.
    Realiza las validaciones cruzadas entre documentos (Fase 1).
    """

    def evaluate(self, raw_docs: Dict[str, Any]) -> List[str]:
        errors = []

        # 1. Validación de Documentos Obligatorios
        required_docs = {
            EducaDocumentCode.FINS.value: "Ficha de Inscripción (FINS)",
            EducaDocumentCode.DJ.value: "Declaración Jurada (DJ)",
            EducaDocumentCode.DNI_BENEFICIARY.value: "DNI del Beneficiario (Niño/a)",
            EducaDocumentCode.DNI_APODERADO.value: "DNI del Apoderado"
        }
        
        for doc_code, doc_name in required_docs.items():
            if not raw_docs.get(doc_code):
                errors.append(f"Falta procesar o adjuntar el documento obligatorio: {doc_name}.")

        # Hidratar diccionarios hacia modelos Pydantic
        fins_dict = raw_docs.get(EducaDocumentCode.FINS.value) or {}
        dj_dict = raw_docs.get(EducaDocumentCode.DJ.value) or {}
        dnibef_dict = raw_docs.get(EducaDocumentCode.DNI_BENEFICIARY.value) or {}
        
        fins_raw = FinsRaw(**fins_dict)
        dj_raw = DjRaw(**dj_dict)
        dnibef_raw = DniRaw(**dnibef_dict)
        
        # Validación cruzada de DNI de Beneficiario usando tipado estricto
        beneficiary_dnis = []
        
        # FINS
        if raw_docs.get("FINS"):
            if fins_raw.child_dni:
                beneficiary_dnis.append(("Ficha de Inscripción", fins_raw.child_dni))
            else:
                errors.append("Falta el DNI del niño en la Ficha de Inscripción (FINS).")
                
        # DJ
        if raw_docs.get("DJ"):
            if dj_raw.child_dni:
                beneficiary_dnis.append(("Declaración Jurada", dj_raw.child_dni))
            else:
                errors.append("Falta el DNI del niño en la Declaración Jurada (DJ).")
                
        # DNI Beneficiario
        if raw_docs.get("DNIBE"):
            if dnibef_raw.DocumentNumber:
                beneficiary_dnis.append(("DNI Beneficiario (Documento)", dnibef_raw.DocumentNumber))
            else:
                errors.append("No se pudo leer el número de documento en el DNI del Beneficiario.")

        # Check for mismatch
        if beneficiary_dnis:
            # Normalizar quitando espacios para la comparación
            first_dni_normalized = beneficiary_dnis[0][1].replace(" ", "").replace("-", "")
            for doc_name, dni in beneficiary_dnis[1:]:
                if dni.replace(" ", "").replace("-", "") != first_dni_normalized:
                    errors.append(f"Inconsistencia en DNI del Beneficiario: El valor en {beneficiary_dnis[0][0]} no coincide con el de {doc_name}.")
                    break

        return errors
