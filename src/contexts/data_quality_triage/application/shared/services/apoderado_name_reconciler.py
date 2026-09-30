# src/contexts/data_quality_triage/application/shared/services/apoderado_name_reconciler.py

from typing import List, Optional
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins, EnrichedDj, EnrichedAdult
from src.contexts.data_quality_triage.application.educa.mappers.enriched.dni_enriched_mapper import EnrichedDni
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult


class ApoderadoNameReconciler:
    """
    Reconcilia el nombre del apoderado usando 4 fuentes de apellidos:
    - DNIAP (apellido del apoderado en su DNI)
    - DNIBE (apellido del niño en su DNI - con modelo base es el apellido completo)
    - FINS_apoderado (apellido del padre/madre/apoderado en FINS)
    - FINS_niño (apellido del niño en FINS)

    Regla de votación:
    - DNIAP y DNIBE son documentos oficiales (peso alto)
    - FINS es declaración (peso bajo)
    - Gana el apellido con más votos; empate → DNIAP (fuente primaria)
    - Si DNIAP no coincide con madre/padre/apoderado en FINS/DJ → WARNING
    """

    def __init__(
        self,
        dniap: EnrichedDni,      # DNI_APODERADO
        fins: EnrichedFins,      # FINS con adults list
        dnibe: EnrichedDni,      # DNI_BENEFICIARY (DNIBE)
        dj: Optional[EnrichedDj], # DJ (opcional, para corroboración)
        dossier_adults: List[object],  # domain_entity.related_adults.adults
    ):
        self.dniap = dniap
        self.fins = fins
        self.dnibe = dnibe
        self.dj = dj
        self.dossier_adults = dossier_adults

    def reconcile(self) -> List[FieldDiscrepancy]:
        # 1. DNI del apoderado según DNIAP (fuente primaria)
        dni_ap = self._get_norm(self.dniap.document_number)
        nombre_dniap = self._build_full_name(self.dniap.first_name, self.dniap.last_name)
        apellido_dniap = self._get_norm(self.dniap.last_name)

        if not dni_ap or not nombre_dniap:
            return []  # DNIAP sin data usable

        # 2. Buscar coincidencia en FINS (adults list: MOTHER, FATHER, OTHER/guardian)
        fins_match = self._find_fins_adult(dni_ap)
        if not fins_match:
            # 2b. Intentar con DJ como fallback
            dj_match = self._find_dj_adult(dni_ap)
            if not dj_match:
                return [FieldDiscrepancy(
                    field_name="related_adults.apoderado_dniap_dni",
                    expected_pattern=f"DNI {dni_ap} debe coincidir con apoderado en FINS o DJ",
                    actual_value=f"DNIAP: {dni_ap} | FINS adults: {[self._get_norm(a.dni) for a in self.fins.adults]}",
                    rule_description=(
                        f"El apoderado del DNIAP (DNI {dni_ap}: {nombre_dniap}) "
                        f"no coincide con ningún adulto (madre/padre/apoderado) en FINS ni DJ. "
                        f"Verifique que el DNIAP corresponda al apoderado correcto."
                    ),
                    severity="WARNING",
                    document_code="DNIAP"
                )]
            # Usar DJ como fuente de apellido del apoderado
            apellido_fins_ap = self._extract_last_word(dj_match.get("name"))
            fuente_apellido_fins = "DJ"
            nombre_fins_ap = dj_match.get("name")
        else:
            apellido_fins_ap = self._get_norm(fins_match.last_name)
            fuente_apellido_fins = "FINS"
            nombre_fins_ap = self._build_full_name(fins_match.first_name, fins_match.last_name)

        # 3. EXTRAER LOS 4 APELLIDOS
        # A) DNIAP - apellido apoderado
        # B) FINS_apoderado - apellido del padre/madre/apoderado según match
        # C) FINS_niño - apellido del niño en FINS
        apellido_fins_nino = self._extract_last_word(self._get_norm(self.fins.child_last_name))
        
        # D) DNIBE - apellido del niño en DNIBE (modelo actual: apellido completo)
        apellido_dnibe_nino = self._get_norm(self.dnibe.last_name)

        # 4. TABLA DE COINCIDENCIAS (normalizadas a upper/strip)
        coincidencias_raw = {
            "DNIAP": self._get_norm(self.dniap.last_name),
            "FINS_apoderado": self._get_norm(fins_match.last_name) if fins_match else None,
            "FINS_niño": apellido_fins_nino,
            "DNIBE_niño": self._get_norm(self.dnibe.last_name),
        }
        # Si no hubo match en FINS, no contamos FINS_apoderado
        if not fins_match:
            coincidencias_raw.pop("FINS_apoderado", None)

        # Normalizar para comparar (upper, strip)
        coincidencias = {k: (v.upper().strip() if v else None) for k, v in coincidencias_raw.items()}

        # 5. VOTACIÓN: apellido con más fuentes
        votos = {}
        for fuente, ape in coincidencias.items():
            if ape:
                votos[ape] = votos.get(ape, 0) + 1

        if not votos:
            return []  # Sin apellidos para comparar

        apellido_ganador = max(votos, key=votos.get)
        fuentes_ganadoras = [f for f, a in coincidencias.items() if a == apellido_ganador]

        # 6. DECISIÓN DEL NOMBRE
        # Prioridad: DNIAP > FINS_apoderado (si ambos en ganadores, DNIAP gana por ser doc oficial)
        dniap_en_ganadores = coincidencias.get("DNIAP") == apellido_ganador
        fins_ap_en_ganadores = coincidencias.get("FINS_apoderado") == apellido_ganador

        if dniap_en_ganadores:
            elegido = "DNIAP"
            nombre_elegido = self._build_full_name(self.dniap.first_name, self.dniap.last_name)
        elif fins_ap_en_ganadores:
            elegido = "FINS"
            # Buscar el nombre completo en FINS
            fins_ap = self._find_fins_adult(dni_ap)
            nombre_elegido = self._build_full_name(fins_ap.first_name, fins_ap.last_name) if fins_ap else None
        else:
            elegido = "DNIAP"  # fallback seguro
            nombre_elegido = self._build_full_name(self.dniap.first_name, self.dniap.last_name)

        # 7. GENERAR CORRECCIÓN SI EL NOMBRE CAMBIA EN EL DOSSIER
        for i, adulto in enumerate(self.dossier_adults):
            dni_adulto = self._get_norm(getattr(adulto, "dni", None))
            if dni_adulto == dni_ap:
                nombre_actual = self._get_norm(getattr(adulto, "full_name", None))
                if nombre_elegido and nombre_elegido != nombre_actual:
                    # Construir descripción legible
                    coincidencias_str = ", ".join(f"{k}='{v}'" for k, v in coincidencias_raw.items())
                    desc = (
                        f"Apoderado DNI {dni_ap}: nombre reconciliado → '{nombre_elegido}' (fuente: {elegido}). "
                        f"Votación apellidos: {coincidencias_str}. "
                        f"Ganador: '{list(votos.keys())[list(votos.values()).index(max(votos.values()))]}' "
                        f"respaldado por {fuentes_ganadoras}."
                    )
                    return [FieldDiscrepancy(
                        field_name=f"related_adults.adults[{i}].full_name",
                        expected_pattern=nombre_elegido,
                        actual_value=nombre_actual,
                        rule_description=desc,
                        severity="INFO",
                        document_code="DNIAP"
                    )]
                break

        return []

    # --- Helpers ---
    @staticmethod
    def _get_norm(field) -> Optional[str]:
        if field is None:
            return None
        val = getattr(field, "normalized_value", None)
        if val is None:
            val = getattr(field, "value", None)
        if val is None:
            val = field if isinstance(field, str) else None
        if hasattr(val, "normalized_value"):  # EnrichedField anidado
            val = val.normalized_value
        return val.strip() if isinstance(val, str) and val.strip() else None

    @staticmethod
    def _build_full_name(first_field, last_field) -> Optional[str]:
        fn = ApoderadoNameReconciler._get_norm(first_field)
        ln = ApoderadoNameReconciler._get_norm(last_field)
        if fn and ln:
            return f"{fn} {ln}".strip()
        return fn or ln

    @staticmethod
    def _extract_last_word(text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        parts = text.split()
        return parts[-1] if parts else None

    def _find_fins_adult(self, dni_ap: str) -> Optional[EnrichedAdult]:
        """Busca en FINS.adults el adulto cuyo DNI coincide con dni_ap."""
        for adult in self.fins.adults:
            if self._get_norm(adult.dni) == dni_ap:
                return adult
        return None

    def _find_dj_adult(self, dni_ap: str) -> Optional[dict]:
        """Busca en DJ el adulto (madre/padre/guardian) cuyo DNI coincide."""
        if not self.dj:
            return None
        # Guardian
        if self._get_norm(self.dj.guardian_dni) == dni_ap:
            return {"name": self._build_full_name(self.dj.parents_father_name, self.dj.parents_father_name) or 
                          self._build_full_name(self.dj.parents_mother_name, self.dj.parents_mother_name)}
        # Father
        if self._get_norm(self.dj.parents_father_dni) == dni_ap:
            return {"name": self._get_norm(self.dj.parents_father_name)}
        # Mother
        if self._get_norm(self.dj.parents_mother_dni) == dni_ap:
            return {"name": self._get_norm(self.dj.parents_mother_name)}
        return None