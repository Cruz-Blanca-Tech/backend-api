from typing import Any, Optional
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins, EnrichedDj
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult

class FamilyDomainMapper:
    def map(self, enriched_fins: EnrichedFins, enriched_dj: Optional[EnrichedDj] = None, enriched_dniap: Any = None) -> FamilyData:
        adults = []
        def normalize_role(raw_role):
            if not raw_role: return "OTHER"
            r_str = str(raw_role).upper()
            if hasattr(raw_role, 'value'): r_str = str(raw_role.value).upper()
            if r_str in ["MOTHER", "FATHER"]: return r_str
            return "OTHER"

        import difflib
        def is_same_person(a1: RelatedAdult, a2_dni: Optional[str], a2_name: Optional[str]) -> bool:
            if a1.dni and a2_dni and a1.dni == a2_dni:
                return True
            if a1.full_name and a2_name:
                n1 = a1.full_name.lower().strip()
                n2 = a2_name.lower().strip()
                if n1 == n2:
                    return True
                ratio = difflib.SequenceMatcher(None, n1, n2).ratio()
                if ratio > 0.85:
                    return True
                # Si tienen al menos 2 palabras en común (ej. nombre y apellido)
                set1, set2 = set(n1.split()), set(n2.split())
                if len(set1) > 1 and len(set2) > 1 and len(set1.intersection(set2)) >= 2:
                    return True
                # Si uno es una sola palabra (ej. "SANDOVAL") y el otro tiene múltiples ("LAURA SONDOVAL URGUIA")
                if len(set1) == 1 or len(set2) == 1:
                    single_word = list(set1)[0] if len(set1) == 1 else list(set2)[0]
                    other_words = set2 if len(set1) == 1 else set1
                    for w in other_words:
                        if difflib.SequenceMatcher(None, single_word, w).ratio() > 0.80:
                            return True
            return False

        guardian_dni = None
        dj_signer_dni = None
        fins_guardian_dni = None
        
        # 1. Extraer de DJ si existe
        if enriched_dj and enriched_dj.guardian_dni.normalized_value:
            guardian_dni = str(enriched_dj.guardian_dni.normalized_value)
            dj_signer_dni = guardian_dni
            
        for a in enriched_fins.adults:
            try:
                first_name = str(a.first_name.normalized_value) if a.first_name and a.first_name.normalized_value else ""
                last_name = str(a.last_name.normalized_value) if a.last_name and a.last_name.normalized_value else ""
                computed_full_name = f"{first_name} {last_name}".strip()

                dni_val = a.dni.normalized_value if a.dni else None
                phone_val = a.phone.normalized_value if a.phone else None
                norm_role = normalize_role(a.role)
                raw_role_str = str(a.role).upper() if a.role else ""

                if dni_val or computed_full_name:
                    # Check for duplicates
                    existing = next((ex for ex in adults if is_same_person(ex, dni_val, computed_full_name)), None)
                    if existing:
                        # Upgrade role if needed
                        if existing.relationship == "OTHER" and norm_role in ["MOTHER", "FATHER"]:
                            existing.relationship = norm_role
                        # Merge missing fields
                        if not existing.dni and dni_val: existing.dni = dni_val
                        if not existing.phone and phone_val: existing.phone = phone_val
                        
                        # Si el original duplicado era apoderado, heredar al guardian_dni
                        if raw_role_str in ["TUTOR", "APODERADO"]:
                            if existing.dni: fins_guardian_dni = existing.dni
                            if not guardian_dni and existing.dni:
                                guardian_dni = existing.dni
                    else:
                        adults.append(RelatedAdult(
                            relationship=norm_role,
                            dni=dni_val,
                            full_name=computed_full_name or None,
                            phone=phone_val
                        ))
                        # Si es apoderado, guardarlo
                        if raw_role_str in ["TUTOR", "APODERADO"]:
                            if dni_val: fins_guardian_dni = dni_val
                            if not guardian_dni and dni_val:
                                guardian_dni = dni_val
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Error mapeando adulto en FamilyDomainMapper: {e}")
                continue

        # 1.5 Extraer Padre y Madre de la DJ como fallback si no vinieron en la FINS
        if enriched_dj:
            # Padre de la DJ
            f_dni = str(enriched_dj.parents_father_dni.normalized_value) if enriched_dj.parents_father_dni and enriched_dj.parents_father_dni.normalized_value else None
            f_name = str(enriched_dj.parents_father_name.normalized_value).strip() if enriched_dj.parents_father_name and enriched_dj.parents_father_name.normalized_value else None
            if f_dni or f_name:
                existing_f = next((ex for ex in adults if is_same_person(ex, f_dni, f_name)), None)
                if existing_f:
                    if not existing_f.dni and f_dni: existing_f.dni = f_dni
                    if not existing_f.full_name and f_name: existing_f.full_name = f_name
                    if existing_f.relationship == "OTHER": existing_f.relationship = "FATHER"
                else:
                    adults.append(RelatedAdult(relationship="FATHER", dni=f_dni, full_name=f_name))
            
            # Madre de la DJ
            m_dni = str(enriched_dj.parents_mother_dni.normalized_value) if enriched_dj.parents_mother_dni and enriched_dj.parents_mother_dni.normalized_value else None
            m_name = str(enriched_dj.parents_mother_name.normalized_value).strip() if enriched_dj.parents_mother_name and enriched_dj.parents_mother_name.normalized_value else None
            if m_dni or m_name:
                existing_m = next((ex for ex in adults if is_same_person(ex, m_dni, m_name)), None)
                if existing_m:
                    if not existing_m.dni and m_dni: existing_m.dni = m_dni
                    if not existing_m.full_name and m_name: existing_m.full_name = m_name
                    if existing_m.relationship == "OTHER": existing_m.relationship = "MOTHER"
                else:
                    adults.append(RelatedAdult(relationship="MOTHER", dni=m_dni, full_name=m_name))
            
        # 2. Si no hay DJ, pero se extrajo el DNI físico del Apoderado (DNIAP)
        if not guardian_dni and enriched_dniap and enriched_dniap.document_number.normalized_value:
            guardian_dni = str(enriched_dniap.document_number.normalized_value)
            
            full_name = ""
            if enriched_dniap.first_name.normalized_value:
                full_name += str(enriched_dniap.first_name.normalized_value)
            if enriched_dniap.last_name.normalized_value:
                full_name += " " + str(enriched_dniap.last_name.normalized_value)
            computed_name = full_name.strip() or None

            # Verificamos si este adulto ya está en la lista (Deduplicación)
            existing = next((ex for ex in adults if is_same_person(ex, guardian_dni, computed_name)), None)
            if existing:
                if not existing.dni and guardian_dni: existing.dni = guardian_dni
            else:
                adults.append(RelatedAdult(
                    relationship="OTHER",
                    dni=guardian_dni,
                    full_name=computed_name
                ))
                
        from src.contexts.data_quality_triage.domain.shared.value_objects.adult_role import AdultRole

        emergency_contact_phone = enriched_fins.emergency_contact_phone.normalized_value if enriched_fins.emergency_contact_phone else None
        emergency_contact_dni = None
        
        # 1. Try to match explicit phone
        if emergency_contact_phone:
            matched_adult = next((a for a in adults if a.phone == emergency_contact_phone), None)
            if matched_adult:
                emergency_contact_dni = matched_adult.dni

        def get_role_str(rel):
            if hasattr(rel, 'value'): return str(rel.value).upper()
            return str(rel).upper()
            
        # 2. Fallback
        if not emergency_contact_dni:
                
            apoderado = next((a for a in adults if a.dni == guardian_dni and a.phone), None)
            madre = next((a for a in adults if a.relationship and get_role_str(a.relationship) == "MOTHER" and a.phone), None)
            padre = next((a for a in adults if a.relationship and get_role_str(a.relationship) == "FATHER" and a.phone), None)
            
            if apoderado:
                emergency_contact_dni = apoderado.dni
            elif madre:
                emergency_contact_dni = madre.dni
            elif padre:
                emergency_contact_dni = padre.dni

        # 3. AUTO-APROBACIÓN PARA FAMILIAS MONOPARENTALES / ÚNICO FAMILIAR
        # Si el sistema extrajo exactamente a 1 adulto y este tiene DNI y teléfono,
        # asume automáticamente que es el Apoderado y el Contacto de Emergencia.
        if len(adults) == 1:
            unique_adult = adults[0]
            if unique_adult.dni and unique_adult.phone:
                if not guardian_dni:
                    guardian_dni = unique_adult.dni
                if not emergency_contact_dni:
                    emergency_contact_dni = unique_adult.dni

        # 4. AUTO-CORRECCIÓN DE GÉNERO (Fallback si la IA se equivoca)
        female_names = {"laura", "maria", "carmen", "ana", "rosa", "marta", "julia", "elena", "patricia", "lucia", "sofia", "isabel", "paula", "silvia", "teresa", "beatriz", "claudia", "sara", "andrea", "raquel", "susana", "natalia", "cristina", "victoria", "rocio", "diana", "monica", "alicia", "celia", "gloria", "juana", "flor", "margarita", "luz", "milagros", "evelin"}
        male_names = {"mario", "juan", "pedro", "luis", "carlos", "jose", "manuel", "francisco", "david", "javier", "daniel", "antonio", "miguel", "angel", "alejandro", "diego", "jorge", "pablo", "alvaro", "fernando", "ruben", "ivan", "oscar", "victor", "raul", "hector", "marcos", "alberto", "rafael", "sergio", "julio", "cesar", "luis"}
        
        for a in adults:
            if not a.full_name or a.relationship == "OTHER": continue
            first_name = a.full_name.split()[0].lower()
            if a.relationship == "FATHER" and first_name in female_names:
                a.relationship = "MOTHER"
            elif a.relationship == "MOTHER" and first_name in male_names:
                a.relationship = "FATHER"
                
        validation_issues = []

        
        # 4. Post-merge deduplication
        # As DJ might have added DNIs to name-only adults, we might now have multiple adults with the same DNI.
        final_adults = []
        for a in adults:
            if not a.dni:
                final_adults.append(a)
                continue
            existing = next((ex for ex in final_adults if ex.dni == a.dni), None)
            if existing:
                if not existing.full_name and a.full_name: existing.full_name = a.full_name
                if not existing.phone and a.phone: existing.phone = a.phone
                if existing.relationship == "OTHER" and a.relationship != "OTHER": existing.relationship = a.relationship
            else:
                final_adults.append(a)
        adults = final_adults

        has_father = False
        has_mother = False
        other_count = 0
        
        for a in adults:
            r_str = get_role_str(a.relationship)
            if r_str == "FATHER":
                has_father = True
            elif r_str == "MOTHER":
                has_mother = True
            elif r_str in ["OTHER", "APODERADO", "DESCONOCIDO"]:
                other_count += 1
                
        if not (has_father or has_mother):
            validation_issues.append("Debe registrar al menos al padre o a la madre.")
            
        if other_count > 1:
            validation_issues.append("Solo se permite un familiar sin relación específica ('OTHER').")
                
        return FamilyData(
            adults=adults,
            guardian_dni=guardian_dni,
            fins_guardian_dni=fins_guardian_dni,
            dj_signer_dni=dj_signer_dni,
            emergency_contact_dni=emergency_contact_dni,
            validation_issues=validation_issues
        )
