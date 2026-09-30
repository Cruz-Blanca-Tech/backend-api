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

        # Identidad del niño beneficiario (para evitar que el niño sea agregado como
        # su propio padre/madre y para validar coherencia de apellidos paterno/materno).
        child_first = (
            str(enriched_fins.child_first_name.normalized_value).strip()
            if enriched_fins and enriched_fins.child_first_name and enriched_fins.child_first_name.normalized_value
            else ""
        )
        child_last = (
            str(enriched_fins.child_last_name.normalized_value).strip()
            if enriched_fins and enriched_fins.child_last_name and enriched_fins.child_last_name.normalized_value
            else ""
        )
        child_full_name = f"{child_first} {child_last}".strip() or None
        child_dni_val = (
            str(enriched_fins.child_dni.normalized_value).strip()
            if enriched_fins and enriched_fins.child_dni and enriched_fins.child_dni.normalized_value
            else None
        )
        child_last_tokens = [t.lower() for t in child_last.split() if t.strip()]
        child_paternal = child_last_tokens[0] if len(child_last_tokens) >= 1 else None
        child_maternal = child_last_tokens[-1] if len(child_last_tokens) >= 2 else None

        def is_child_person(cand_dni: Optional[str], cand_name: Optional[str]) -> bool:
            if child_dni_val and cand_dni and str(cand_dni).strip() == child_dni_val:
                return True
            if not child_full_name or not cand_name:
                return False
            c1 = child_full_name.lower().strip()
            c2 = cand_name.lower().strip()
            if c1 == c2 or difflib.SequenceMatcher(None, c1, c2).ratio() > 0.85:
                return True
            # Si comparte ambos apellidos del niño (paterno y materno) y además algún nombre de pila del niño
            tokens_cand = set(c2.split())
            tokens_child_first = {t.lower() for t in child_first.split() if len(t) > 2}
            if (
                child_paternal
                and child_maternal
                and child_paternal != child_maternal
                and child_paternal in tokens_cand
                and child_maternal in tokens_cand
                and (not tokens_child_first or bool(tokens_child_first.intersection(tokens_cand)))
            ):
                return True
            return False
        
        # 1. Extraer de DJ si existe
        if enriched_dj and enriched_dj.guardian_dni and enriched_dj.guardian_dni.normalized_value:
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

                # Nunca agregar al propio niño beneficiario como adulto/padre/madre
                if is_child_person(dni_val, computed_full_name):
                    continue

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
            f_dni = str(enriched_dj.parents_father_dni.normalized_value) if enriched_dj.parents_father_dni and enriched_dj.parents_father_dni.normalized_value else None
            f_name = str(enriched_dj.parents_father_name.normalized_value).strip() if enriched_dj.parents_father_name and enriched_dj.parents_father_name.normalized_value else None
            m_dni = str(enriched_dj.parents_mother_dni.normalized_value) if enriched_dj.parents_mother_dni and enriched_dj.parents_mother_dni.normalized_value else None
            m_name = str(enriched_dj.parents_mother_name.normalized_value).strip() if enriched_dj.parents_mother_name and enriched_dj.parents_mother_name.normalized_value else None
            dj_c_dni = str(enriched_dj.child_dni.normalized_value) if enriched_dj.child_dni and enriched_dj.child_dni.normalized_value else None
            dj_c_name = str(enriched_dj.child_name.normalized_value).strip() if getattr(enriched_dj, "child_name", None) and enriched_dj.child_name.normalized_value else None

            # Detectar desfase de filas en la DJ:
            # Ocurre cuando el OCR coloca al adulto firmante en child_name/child_dni y al
            # niño beneficiario en parents_father_name (o parents_mother_name), desplazando
            # el DNI del niño al siguiente campo de padre/madre.
            f_is_child = is_child_person(f_dni, f_name)
            m_is_child = is_child_person(m_dni, m_name)

            if f_is_child:
                # Si el niño cayó en parents_father_name sin DNI y el DNI del niño cayó desplazado en parents_mother_dni
                if not f_dni and m_dni and not is_child_person(None, m_name):
                    m_dni = None
                f_name = None
                f_dni = None

            if m_is_child:
                m_name = None
                m_dni = None

            # Si en child_name de la DJ vino en realidad un adulto (desfase de la primera línea de la DJ)
            if (f_is_child or m_is_child) and (dj_c_name or dj_c_dni) and not is_child_person(dj_c_dni, dj_c_name):
                existing_c = next((ex for ex in adults if is_same_person(ex, dj_c_dni, dj_c_name)), None)
                if existing_c:
                    if not existing_c.dni and dj_c_dni:
                        existing_c.dni = dj_c_dni
                    if not existing_c.full_name and dj_c_name:
                        existing_c.full_name = dj_c_name
                elif dj_c_name:
                    adults.append(RelatedAdult(relationship="OTHER", dni=dj_c_dni, full_name=dj_c_name))
                if dj_c_dni:
                    if not dj_signer_dni:
                        dj_signer_dni = dj_c_dni
                    if not guardian_dni:
                        guardian_dni = dj_c_dni

            # Padre de la DJ
            if f_dni or f_name:
                existing_f = next((ex for ex in adults if is_same_person(ex, f_dni, f_name)), None)
                if existing_f:
                    if not existing_f.dni and f_dni: existing_f.dni = f_dni
                    if not existing_f.full_name and f_name: existing_f.full_name = f_name
                    if existing_f.relationship == "OTHER": existing_f.relationship = "FATHER"
                else:
                    adults.append(RelatedAdult(relationship="FATHER", dni=f_dni, full_name=f_name))
            
            # Madre de la DJ
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

        # 4. AUTO-CORRECCIÓN DE PADRE / MADRE POR GÉNERO DEL NOMBRE Y COHERENCIA DE APELLIDOS
        female_names = {
            "laura", "maria", "carmen", "ana", "rosa", "marta", "martha", "julia", "elena",
            "patricia", "lucia", "sofia", "isabel", "paula", "silvia", "teresa", "beatriz",
            "claudia", "sara", "sarah", "andrea", "raquel", "susana", "natalia", "cristina",
            "victoria", "rocio", "diana", "monica", "alicia", "celia", "gloria", "juana",
            "flor", "margarita", "luz", "milagros", "evelin", "evelyn", "jackeline",
            "jacqueline", "jakeline", "mayra", "maira", "nativel", "elizabeth", "elisabeth",
            "gabriela", "veronica", "vanessa", "vanesa", "karina", "karla", "carla", "paola",
            "pilar", "lourdes", "maritza", "marisol", "maribel", "mariela", "miriam", "mirian",
            "nancy", "norma", "olga", "gladys", "irma", "ines", "irene", "hilda", "haydee",
            "edith", "doris", "dora", "delia", "consuelo", "cecilia", "blanca", "bertha",
            "aurora", "amalia", "adriana", "alejandra", "fiorella", "fabiola", "estefania",
            "daniela", "cynthia", "cintia", "camila", "brenda", "angela", "angelica", "jessica",
            "jesica", "jenny", "jennifer", "johana", "johanna", "julissa", "katherine", "katia",
            "kelly", "lady", "leticia", "liliana", "lisbeth", "liz", "lizbeth", "lorena",
            "luisa", "magaly", "magali", "mercedes", "melissa", "nadia", "nelly", "noemi",
            "pamela", "rebeca", "rita", "rosario", "roxana", "ruth", "sandra", "sheyla",
            "shirley", "sonia", "soledad", "tania", "tatiana", "valeria", "vilma", "violeta",
            "virginia", "viviana", "wendy", "ximena", "yanet", "yaneth", "yesenia", "yovana",
            "yovanna", "yulissa", "zoraida", "zulema",
        }
        male_names = {
            "mario", "juan", "pedro", "luis", "carlos", "jose", "manuel", "francisco",
            "david", "javier", "daniel", "antonio", "miguel", "angel", "alejandro", "diego",
            "jorge", "pablo", "alvaro", "fernando", "ruben", "ivan", "oscar", "victor",
            "raul", "hector", "marcos", "alberto", "rafael", "sergio", "julio", "cesar",
            "jonathan", "jhonatan", "jonatan", "jhon", "john", "jhony", "jhonny", "jeffer",
            "jefferson", "jaime", "jesus", "joel", "josue", "julian", "junior", "kevin",
            "bryan", "brayan", "christian", "cristian", "alexander", "alex", "andres",
            "arturo", "augusto", "benjamin", "bernardo", "bruno", "camilo", "claudio",
            "cristobal", "damian", "dario", "darwin", "dennis", "domingo", "edgar", "edison",
            "eduardo", "edwin", "efrain", "elias", "elmer", "emilio", "enrique", "ernesto",
            "esteban", "eugenio", "fabian", "fabricio", "fausto", "federico", "felipe",
            "felix", "fidel", "flavio", "frank", "freddy", "fredy", "gabriel", "genaro",
            "gerardo", "german", "giancarlo", "gilberto", "gonzalo", "gregorio", "guillermo",
            "gustavo", "harold", "henry", "henrry", "hernan", "hugo", "humberto", "idelso",
            "ignacio", "isaac", "isaias", "ismael", "israel", "jairo", "jean", "jeremias",
            "joaquin", "johan", "jordan", "leandro", "leonardo", "leonel", "lorenzo", "lucas",
            "luciano", "marcelo", "marco", "mariano", "martin", "mateo", "matias", "mauricio",
            "max", "maximo", "melvin", "michael", "milton", "moises", "nelson", "nestor",
            "nicolas", "noel", "norberto", "octavio", "omar", "orlando", "oswaldo", "patricio",
            "paul", "percy", "ramiro", "ramon", "renato", "rene", "renzo", "reynaldo",
            "ricardo", "richard", "roberto", "rodolfo", "rodrigo", "roger", "rolando",
            "roman", "romulo", "ronald", "roque", "salvador", "samuel", "santiago", "santos",
            "saul", "sebastian", "segundo", "simon", "teodoro", "teofilo", "timoteo", "tito",
            "tomas", "ulises", "valentin", "vicente", "vladimir", "walter", "wilder",
            "william", "willy", "wilmer", "wilson", "xavier", "yuri", "zacarias",
        }

        for a in adults:
            if not a.full_name:
                continue
            tokens = [t.lower() for t in a.full_name.split() if t.strip()]
            if not tokens:
                continue
            # Los primeros tokens son nombres de pila (si hay >=3 tokens, los últimos 2 suelen ser apellidos)
            given_tokens = tokens[:-2] if len(tokens) >= 3 else tokens[:1]
            surname_tokens = tokens[-2:] if len(tokens) >= 3 else tokens[1:]

            is_male = any(t in male_names for t in given_tokens) and not any(t in female_names for t in given_tokens)
            is_female = any(t in female_names for t in given_tokens) and not any(t in male_names for t in given_tokens)

            # Coherencia por apellido paterno/materno del niño (ej. niño PAREDES ESCOBAR:
            # adulto con apellido PAREDES -> línea paterna; adulto con apellido ESCOBAR -> línea materna)
            matches_paternal = False
            matches_maternal = False
            if child_paternal and child_maternal and child_paternal != child_maternal and surname_tokens:
                matches_paternal = any(
                    difflib.SequenceMatcher(None, st, child_paternal).ratio() >= 0.85
                    for st in surname_tokens
                )
                matches_maternal = any(
                    difflib.SequenceMatcher(None, st, child_maternal).ratio() >= 0.85
                    for st in surname_tokens
                )

            inferred_role = None
            if is_male or (not is_female and matches_paternal and not matches_maternal):
                inferred_role = "FATHER"
            elif is_female or (not is_male and matches_maternal and not matches_paternal):
                inferred_role = "MOTHER"

            if inferred_role:
                if a.relationship in ("FATHER", "MOTHER") and a.relationship != inferred_role:
                    a.relationship = inferred_role
                elif a.relationship == "OTHER" and (
                    (inferred_role == "FATHER" and matches_paternal)
                    or (inferred_role == "MOTHER" and matches_maternal)
                ):
                    a.relationship = inferred_role
                
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
