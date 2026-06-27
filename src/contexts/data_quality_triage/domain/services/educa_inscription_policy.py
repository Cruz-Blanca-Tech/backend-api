from typing import Dict, Any, List
from src.contexts.data_quality_triage.domain.services.dossier_policy import DossierPolicy
from src.contexts.data_quality_triage.domain.value_objects.raw_data.fins_raw import FichaInscripcionRaw
from src.contexts.data_quality_triage.domain.value_objects.raw_data.dj_raw import DeclaracionJuradaRaw
from src.contexts.data_quality_triage.domain.value_objects.raw_data.dni_raw import DniRaw

class EducaInscriptionPolicy(DossierPolicy):
    """
    Política específica para la actividad Educa Inscription.
    Realiza las validaciones cruzadas entre documentos (Fase 1).
    """

    def evaluate(self, raw_docs: Dict[str, Any]) -> List[str]:
        errors = []

        fins_raw: FichaInscripcionRaw = raw_docs.get("FINS")
        dj_raw: DeclaracionJuradaRaw = raw_docs.get("DJ")
        dnibef_raw: DniRaw = raw_docs.get("DNIBEF")
        
        # Validación cruzada de DNI de Beneficiario
        beneficiary_dnis = []
        if fins_raw and fins_raw.child_dni:
            beneficiary_dnis.append(("Ficha de Inscripción", fins_raw.child_dni))
        if dj_raw and dj_raw.child_dni:
            beneficiary_dnis.append(("Declaración Jurada", dj_raw.child_dni))
        if dnibef_raw and dnibef_raw.DocumentNumber:
            beneficiary_dnis.append(("DNI Beneficiario", dnibef_raw.DocumentNumber))

        # Check for mismatch
        if beneficiary_dnis:
            # Normalizar quitando espacios para la comparación
            first_dni_normalized = beneficiary_dnis[0][1].replace(" ", "").replace("-", "")
            for doc_name, dni in beneficiary_dnis[1:]:
                if dni.replace(" ", "").replace("-", "") != first_dni_normalized:
                    errors.append(f"Inconsistencia en DNI del Beneficiario: El valor en {beneficiary_dnis[0][0]} no coincide con el de {doc_name}.")
                    break

        return errors
