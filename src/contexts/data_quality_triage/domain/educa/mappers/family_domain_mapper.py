from typing import Any, Optional, List
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins, EnrichedDj
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult

class FamilyDomainMapper:
    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        if not s1 or not s2:
            return max(len(s1 or ""), len(s2 or ""))
        s1, s2 = s1.lower(), s2.lower()
        if len(s1) < len(s2):
            return FamilyDomainMapper._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    @staticmethod
    def _deduplicate_adults(adults: List[RelatedAdult]) -> tuple[List[RelatedAdult], List[str]]:
        def get_role_str(rel):
            if hasattr(rel, 'value'): return str(rel.value).upper()
            return str(rel).upper()

        principals = []
        secondaries = []
        for a in adults:
            role = get_role_str(a.relationship)
            if role in ["FATHER", "MOTHER", "PADRE", "MADRE"]:
                principals.append(a)
            else:
                secondaries.append(a)

        deduplicated = list(principals)
        warnings = []
        for sec in secondaries:
            is_duplicate = False
            for prin in principals:
                dni_dist = 999
                if sec.dni and prin.dni:
                    dni_dist = FamilyDomainMapper._levenshtein_distance(str(sec.dni), str(prin.dni))
                
                name_dist = 999
                if sec.full_name and prin.full_name:
                    name_dist = FamilyDomainMapper._levenshtein_distance(str(sec.full_name), str(prin.full_name))
                
                if dni_dist <= 1 or name_dist <= 3:
                    is_duplicate = True
                    
                    # Generar Warning solo si el DNI es diferente (ignoramos pequeñas diferencias de nombre)
                    if sec.dni and prin.dni and str(sec.dni) != str(prin.dni):
                        warnings.append(
                            f"Se unificó al adulto '{sec.full_name or sec.dni}' con '{prin.full_name or prin.dni}' "
                            f"pero sus DNIs difieren en la lectura del OCR ({sec.dni} vs {prin.dni}). Revisar documento físico."
                        )

                    # Si el clon (secundario) capturó un teléfono que el principal no, fucionalos
                    if sec.phone and not prin.phone:
                        prin.phone = sec.phone
                    break
            
            if not is_duplicate:
                deduplicated.append(sec)

        # Límite de 1 por rol (1 Padre, 1 Madre, 1 Otro)
        final_adults = []
        roles_seen = set()
        
        for adult in deduplicated:
            role = get_role_str(adult.relationship)
            # Normalizar el rol para el set
            if role in ["FATHER", "PADRE"]:
                role_key = "FATHER"
            elif role in ["MOTHER", "MADRE"]:
                role_key = "MOTHER"
            else:
                role_key = "OTHER"
                
            if role_key in roles_seen:
                warnings.append(
                    f"Se eliminó a un adulto extra con el rol '{role}' ({adult.full_name or adult.dni}) "
                    f"porque el expediente ya cuenta con un adulto registrado con ese mismo rol."
                )
                continue
                
            roles_seen.add(role_key)
            final_adults.append(adult)

        # Truncar a máximo 3 adultos por seguridad extra
        return final_adults[:3], warnings
    def map(self, enriched_fins: EnrichedFins, enriched_dj: Optional[EnrichedDj] = None, enriched_dniap: Any = None) -> FamilyData:
        adults = []
        for a in enriched_fins.adults:
            try:
                first_name = str(a.first_name.normalized_value) if a.first_name and a.first_name.normalized_value else ""
                last_name = str(a.last_name.normalized_value) if a.last_name and a.last_name.normalized_value else ""
                computed_full_name = f"{first_name} {last_name}".strip()

                dni_val = a.dni.normalized_value if a.dni else None
                phone_val = a.phone.normalized_value if a.phone else None

                if dni_val or computed_full_name:
                    adults.append(RelatedAdult(
                        relationship=a.role if a.role else "desconocido",
                        dni=dni_val,
                        full_name=computed_full_name or None,
                        phone=phone_val
                    ))
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Error mapeando adulto en FamilyDomainMapper: {e}")
                continue
        
        # 1. Obtenemos nombre preciso y DNI desde el documento DNIAP (si existe)
        apoderado_dniap_dni = None
        apoderado_dniap_name = None
        if enriched_dniap:
            if enriched_dniap.document_number and enriched_dniap.document_number.normalized_value:
                apoderado_dniap_dni = str(enriched_dniap.document_number.normalized_value)
            
            first = str(enriched_dniap.first_name.normalized_value) if enriched_dniap.first_name and enriched_dniap.first_name.normalized_value else ""
            last = str(enriched_dniap.last_name.normalized_value) if enriched_dniap.last_name and enriched_dniap.last_name.normalized_value else ""
            computed = f"{first} {last}".strip()
            if computed:
                apoderado_dniap_name = computed

        # 2. Intentamos obtener el DNI del apoderado desde la Declaración Jurada (como respaldo)
        guardian_dni = apoderado_dniap_dni
        if not guardian_dni and enriched_dj and enriched_dj.guardian_dni and enriched_dj.guardian_dni.normalized_value:
            guardian_dni = str(enriched_dj.guardian_dni.normalized_value)

        # 3. Consolidar la información del DNIAP en la lista de adultos
        if apoderado_dniap_dni:
            # Buscar si el apoderado ya existe en la FINS (por DNI)
            existing_apoderado = next((a for a in adults if a.dni == apoderado_dniap_dni), None)
            
            if existing_apoderado:
                # Si existe, SOBREESCRIBIR el nombre con el del DNIAP (tiene prioridad por mayor calidad OCR)
                if apoderado_dniap_name:
                    existing_apoderado.full_name = apoderado_dniap_name
            else:
                # Si no existe, lo agregamos como un nuevo adulto "apoderado"
                adults.append(RelatedAdult(
                    relationship="apoderado",
                    dni=apoderado_dniap_dni,
                    full_name=apoderado_dniap_name or None
                ))
                
        from src.contexts.data_quality_triage.domain.shared.value_objects.adult_role import AdultRole

        emergency_contact_phone = enriched_fins.emergency_contact_phone.normalized_value if enriched_fins.emergency_contact_phone else None
        emergency_contact_dni = None
        
        # 1. Try to match explicit phone
        if emergency_contact_phone:
            matched_adult = next((a for a in adults if a.phone == emergency_contact_phone), None)
            if matched_adult:
                emergency_contact_dni = matched_adult.dni

        # 2. Fallback
        if not emergency_contact_dni:
            def get_role_str(rel):
                if hasattr(rel, 'value'): return str(rel.value).upper()
                return str(rel).upper()
                
            apoderado = next((a for a in adults if a.relationship and get_role_str(a.relationship) in ["OTHER", "APODERADO"] and a.phone), None)
            madre = next((a for a in adults if a.relationship and get_role_str(a.relationship) == "MOTHER" and a.phone), None)
            padre = next((a for a in adults if a.relationship and get_role_str(a.relationship) == "FATHER" and a.phone), None)
            
            if apoderado:
                emergency_contact_dni = apoderado.dni
            elif madre:
                emergency_contact_dni = madre.dni
            elif padre:
                emergency_contact_dni = padre.dni
                
        # 3. Deduplicación final y captura de alertas
        adults, deduplication_warnings = self._deduplicate_adults(adults)
        
        return FamilyData(
            adults=adults,
            guardian_dni=guardian_dni,
            emergency_contact_dni=emergency_contact_dni,
            validation_issues=deduplication_warnings
        )
