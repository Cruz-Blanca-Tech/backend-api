import unicodedata
import re
from typing import Tuple, List, Optional

def normalize_name_token(text: str) -> str:
    """Elimina tildes, números, caracteres especiales y convierte a mayúsculas."""
    if not text:
        return ""
    text = "".join(
        c for c in unicodedata.normalize('NFD', str(text))
        if unicodedata.category(c) != 'Mn'
    )
    text = re.sub(r'[0-9]+', ' ', text)
    return re.sub(r'[^A-Z\s]', ' ', text.upper()).strip()

def get_person_surnames(full_name: Optional[str]) -> List[str]:
    """
    Extrae los apellidos potenciales de un nombre completo de adulto peruano.
    En Perú: [Nombres...] [Paterno] [Materno]
    """
    if not full_name:
        return []
    clean = normalize_name_token(full_name)
    tokens = clean.split()
    if not tokens:
        return []
    if len(tokens) == 1:
        return tokens
    if len(tokens) == 2:
        return [tokens[1]]
    if len(tokens) == 3:
        return [tokens[1], tokens[2]]
    # 4 o más palabras: los dos últimos suelen ser los apellidos paterno y materno
    return [tokens[-2], tokens[-1]]

def get_primary_paternal_surname(full_name: Optional[str]) -> Optional[str]:
    """Devuelve el primer apellido (paterno) de la persona."""
    if not full_name:
        return None
    clean = normalize_name_token(full_name)
    tokens = clean.split()
    if not tokens:
        return None
    if len(tokens) == 1:
        return tokens[0]
    if len(tokens) in (2, 3):
        return tokens[1]
    return tokens[-2]

def is_noise_text(text: str) -> bool:
    """Detecta si un texto de apellido es ruido del escaneo OCR."""
    if not text:
        return True
    t = str(text).strip()
    if len(t) <= 3 and not t.isalpha():
        return True
    if t.endswith(".") and len(t) <= 4:
        return True
    if t.lower() in ["null", "none", "bir.", "bir", "s/n", "s/d", "-", "--"]:
        return True
    return False

def separate_child_name_and_surnames(
    first_name: Optional[str],
    last_name: Optional[str],
    father_full_name: Optional[str] = None,
    mother_full_name: Optional[str] = None
) -> Tuple[str, str]:
    """
    Separa inteligentemente el nombre de pila y los apellidos del niño.
    Si en el campo first_name (nombres) hay palabras que coinciden con los apellidos
    del padre o de la madre, las retira de first_name y las coloca en last_name.
    
    Aplica la ley peruana de apellidos:
    <Nombres> + <Apellido Paterno (Padre)> <Apellido Materno (Madre)>
    """
    raw_fn = re.sub(r'[0-9]+', ' ', str(first_name or "")).strip()
    raw_fn = " ".join(raw_fn.split())
    raw_ln = re.sub(r'[0-9]+', ' ', str(last_name or "")).strip()
    raw_ln = " ".join(raw_ln.split())

    if not raw_fn:
        return raw_fn, raw_ln

    father_surnames = get_person_surnames(father_full_name)
    mother_surnames = get_person_surnames(mother_full_name)
    father_paternal = get_primary_paternal_surname(father_full_name)
    mother_paternal = get_primary_paternal_surname(mother_full_name)

    all_parent_surnames = set(father_surnames + mother_surnames)
    if not all_parent_surnames:
        return raw_fn, raw_ln

    fn_tokens = raw_fn.split()
    if len(fn_tokens) <= 1:
        # Solo tiene una palabra; verificar si esa palabra es un apellido pegado al nombre
        # ej: "ADRIANOMONTENEG"
        last_tok = fn_tokens[0]
        norm_tok = normalize_name_token(last_tok)
        for s in all_parent_surnames:
            if len(s) >= 4:
                # Comprobar sufijo pegado
                for i in range(len(s), 3, -1):
                    sub = s[:i]
                    if norm_tok.endswith(sub) and len(norm_tok) > len(sub) + 2:
                        base = last_tok[:len(norm_tok) - len(sub)]
                        return base, (raw_ln or s)
        return raw_fn, raw_ln

    surnames_in_fn = []
    names_in_fn = list(fn_tokens)

    while len(names_in_fn) > 1:
        last_tok = names_in_fn[-1]
        norm_tok = normalize_name_token(last_tok)
        
        is_match = norm_tok in all_parent_surnames
        matched_surname = norm_tok if is_match else None
        
        # Coincidencia con palabras compuestas o prefijo pegado (ej: VALDEZPAZ o ADRIANOMONTENEG)
        if not is_match:
            for s in all_parent_surnames:
                if len(s) >= 4:
                    if norm_tok.startswith(s) or norm_tok.endswith(s):
                        is_match = True
                        matched_surname = s
                        break
                    # Sufijo pegado (ej. ADRIANOMONTENEG -> base ADRIANO, apellido MONTENEGRO)
                    for i in range(len(s), 3, -1):
                        sub = s[:i]
                        if norm_tok.endswith(sub) and len(norm_tok) > len(sub) + 2:
                            is_match = True
                            matched_surname = s
                            # Cortar el sufijo de la palabra
                            names_in_fn[-1] = last_tok[:len(norm_tok) - len(sub)]
                            break
                    if is_match:
                        break

        if is_match:
            if names_in_fn[-1] == last_tok:
                # La palabra entera era el apellido
                surnames_in_fn.insert(0, names_in_fn.pop())
            else:
                # Solo el sufijo era el apellido; la base quedó en names_in_fn[-1]
                surnames_in_fn.insert(0, matched_surname or last_tok)
                break
        else:
            break

    if not surnames_in_fn:
        return raw_fn, raw_ln

    new_fn = " ".join(names_in_fn)

    # Limpiar y normalizar el last_name existente
    clean_existing_ln = raw_ln.rstrip(".,;").strip()
    norm_existing_ln = normalize_name_token(clean_existing_ln).split()

    # Si el apellido existente es ruido evidente (ej. 'Bir.', 1-2 letras sin sentido)
    if is_noise_text(clean_existing_ln) or (
        len(norm_existing_ln) == 1 and len(norm_existing_ln[0]) <= 3 and norm_existing_ln[0] not in all_parent_surnames
    ):
        clean_existing_ln = ""
        norm_existing_ln = []

    # Determinar qué apellidos de surnames_in_fn deben agregarse
    surnames_to_add = []
    for s in surnames_in_fn:
        norm_s = normalize_name_token(s)
        already_present = any(norm_s == el or norm_s in el or el in norm_s for el in norm_existing_ln)
        if not already_present:
            surnames_to_add.append(s)

    if not surnames_to_add and clean_existing_ln:
        return new_fn, clean_existing_ln

    # Construir el nuevo last_name
    # 1. Si no había apellido válido:
    if not clean_existing_ln:
        father_matched = [s for s in surnames_to_add if normalize_name_token(s) in father_surnames]
        mother_matched = [s for s in surnames_to_add if normalize_name_token(s) in mother_surnames]
        
        final_ln_parts = []
        if father_matched:
            final_ln_parts.extend(father_matched)
        elif father_paternal:
            final_ln_parts.append(father_paternal)

        if mother_matched:
            final_ln_parts.extend(mother_matched)
        elif mother_paternal and mother_paternal not in final_ln_parts:
            final_ln_parts.append(mother_paternal)

        if not final_ln_parts:
            final_ln_parts = surnames_to_add
        new_ln = " ".join(final_ln_parts)
    else:
        father_matched = [s for s in surnames_to_add if normalize_name_token(s) in father_surnames]
        mother_matched = [s for s in surnames_to_add if normalize_name_token(s) in mother_surnames]
        existing_is_mother = any(el in mother_surnames for el in norm_existing_ln)
        existing_is_father = any(el in father_surnames for el in norm_existing_ln)

        if existing_is_mother and father_matched:
            new_ln = " ".join(father_matched + [clean_existing_ln])
        elif existing_is_father and mother_matched:
            new_ln = " ".join([clean_existing_ln] + mother_matched)
        else:
            if father_matched:
                new_ln = " ".join(father_matched + [clean_existing_ln])
            else:
                new_ln = " ".join([clean_existing_ln] + surnames_to_add)

    return new_fn, new_ln
