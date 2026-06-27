from typing import Dict, Any, List
from src.contexts.data_quality_triage.domain.shared.services.dossier_policy import DossierPolicy
from src.contexts.data_quality_triage.domain.educa.value_objects.raw_data.fins_raw import FichaInscripcionRaw
from src.contexts.data_quality_triage.domain.educa.value_objects.raw_data.dj_raw import DeclaracionJuradaRaw
from src.contexts.data_quality_triage.domain.educa.value_objects.raw_data.dni_raw import DniRaw

class EducaInscriptionPolicy(DossierPolicy):
    """
    Política específica para la actividad Educa Inscription.
    Realiza las validaciones cruzadas entre documentos (Fase 1).
    """

    def evaluate(self, raw_docs: Dict[str, Any]) -> List[str]:
        errors = []

        # Hidratar diccionarios hacia modelos Pydantic
        fins_dict = raw_docs.get("FINS") or {}
        dj_dict = raw_docs.get("DJ") or {}
        dnibef_dict = raw_docs.get("DNIBE") or {} # Corregido a DNIBE
        
        fins_raw = FichaInscripcionRaw(**fins_dict)
        dj_raw = DeclaracionJuradaRaw(**dj_dict)
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
