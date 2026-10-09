"""Corrección automática de apellidos del Padre/Madre corroborada por doble lectura.

Cuando el apellido del beneficiario aparece IDÉNTICO en dos lecturas
independientes del OCR — la FINS (`child_last_name`) y el DNI del propio niño
(DNIBE: `last_name`) — la confianza de que esa escritura sea la correcta es
altísima. Si además un adulto (Padre/Madre) trae ese apellido con un error
típico de lectura (TAFOR por TAFUR: una vocal, s/z, b/v, i/y, o una letra de
más/menos), se corrige automáticamente en el dossier y se emite una discrepancia
informativa para que el revisor lo vea y sepa qué se cambió.

Sin la corroboración cruzada NO se corrige nada: una diferencia de una letra
puede ser un apellido distinto de verdad, y en ese caso la regla de coherencia
(`ParentLastNameCoherenceRule`) sigue advirtiendo para revisión manual.
"""

import re
from typing import List, Optional, Tuple

from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription_dossier import EducaInscriptionDossier
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy

# Pares de letras que el OCR confunde al leer apellidos (sustitución de una sola letra).
_OCR_SUBSTITUTION_GROUPS = ("aeiou", "szc", "bv", "iy")


def _normalize(value) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9\s]", "", str(value).lower()).strip()


def _is_plausible_ocr_substitution(ch1: str, ch2: str) -> bool:
    return any(ch1 in group and ch2 in group for group in _OCR_SUBSTITUTION_GROUPS)


def _surname_edit_distance(a: str, b: str) -> int:
    """Distancia de Levenshtein para apellidos cortos."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        current = [i] + [0] * len(b)
        for j, char_b in enumerate(b, 1):
            current[j] = min(
                previous[j] + 1,              # borrado
                current[j - 1] + 1,           # inserción
                previous[j - 1] + (char_a != char_b),  # sustitución
            )
        previous = current
    return previous[-1]


def _ocr_similar(a: str, b: str) -> bool:
    """¿Dos apellidos son el mismo salvo por UN error típico de lectura del OCR?

    Iguales, o a una sola diferencia de distancia de edición:
    - Sustitución de una letra: solo si el par es una confusión típica
      (vocales entre sí, s/z/c, b/v, i/y) — TAFUR/TAFOR, PEREZ/PERES.
    - Una letra de más o de menos (truncamiento) — QUISPES/QUISPE.

    La primera letra debe coincidir, para no casar apellidos distintos que
    difieren en una consonante de arranque (TORRES/CORRES), que no es ruido de
    OCR sino otra familia.
    """
    if not a or not b:
        return False
    if a == b:
        return True
    if a[0] != b[0]:
        return False
    if _surname_edit_distance(a, b) != 1:
        return False
    if len(a) == len(b):
        differing = [(x, y) for x, y in zip(a, b) if x != y]
        return len(differing) == 1 and _is_plausible_ocr_substitution(*differing[0])
    return True


class SurnameAutoCorrector:
    """Detecta apellidos de adultos mal leídos por el OCR y los corrige en el dossier.

    Recibe los apellidos del beneficiario TAL COMO SALIERON de la FINS y del DNI
    del niño (lecturas independientes). Requiere que el apellido aparezca
    idéntico en ambas para corregir; de lo contrario no toca nada.
    """

    def __init__(
        self,
        dossier: EducaInscriptionDossier,
        *,
        fins_last_name: Optional[str] = None,
        child_dni_last_name: Optional[str] = None,
    ):
        self.dossier = dossier
        self.fins_last_name = fins_last_name
        self.child_dni_last_name = child_dni_last_name

    def corroborated_child_surnames(self) -> List[Tuple[str, str]]:
        """Apellidos del niño leídos IDÉNTICOS en la FINS y en su DNI.

        Devuelve [(palabra normalizada, ortografía original)] de la FINS. Dos
        lecturas independientes que coinciden = la escritura es la correcta.
        """
        if not self.fins_last_name or not self.child_dni_last_name:
            return []
        fins_words = self._surname_words(self.fins_last_name)
        dni_words = {norm for norm, _ in self._surname_words(self.child_dni_last_name)}
        return [(norm, original) for norm, original in fins_words if norm in dni_words]

    @staticmethod
    def _surname_words(value) -> List[Tuple[str, str]]:
        out = []
        for word in re.split(r"\s+", str(value or "").strip()):
            norm = _normalize(word)
            if norm:
                out.append((norm, word))
        return out

    def correct(self) -> List[FieldDiscrepancy]:
        """Corrige en el dossier los apellidos de Padre/Madre corroborados.

        Devuelve una discrepancia informativa por cada corrección aplicada,
        para que el revisor vea qué se cambió y por qué.
        """
        corroborated = self.corroborated_child_surnames()
        if not corroborated:
            return []

        notes: List[FieldDiscrepancy] = []
        for index, adult in enumerate(self.dossier.related_adults.adults):
            role = str(adult.relationship).upper()
            if role not in ("FATHER", "MOTHER") or not adult.full_name:
                continue
            notes.extend(self._correct_adult(index, adult, role, corroborated))
        return notes

    def _correct_adult(self, index, adult, role, corroborated) -> List[FieldDiscrepancy]:
        original_name = str(adult.full_name)
        words = original_name.split()
        notes: List[FieldDiscrepancy] = []

        for i, word in enumerate(words):
            norm = _normalize(word)
            if not norm:
                continue
            for norm_surname, spelling in corroborated:
                if norm == norm_surname:
                    # El apellido ya está bien leído: nada que corregir.
                    break
                if _ocr_similar(norm, norm_surname):
                    # Unificación al apellido corroborado (escritura de la FINS).
                    words[i] = spelling
                    notes.append((word, spelling))
                    break

        if notes:
            new_name = " ".join(words)
            adult.full_name = new_name
            return [
                self._build_note(index, role, original_name, new_name, wrong_word, spelling)
                for wrong_word, spelling in notes
            ]
        return []

    def _build_note(self, index, role, original_name, new_name, wrong_word, spelling) -> FieldDiscrepancy:
        label = "el Padre" if role == "FATHER" else "la Madre"
        return FieldDiscrepancy(
            field_name=f"related_adults.adults[{index}].full_name",
            expected_pattern=new_name,
            actual_value=original_name,
            rule_description=(
                f"Corrección automática: el apellido de {label} se leyó '{wrong_word}' "
                f"y se unificó a '{spelling}', porque la FINS y el DNI del niño/a "
                f"coinciden en ese apellido (error típico de lectura del OCR)."
            ),
            severity="INFO",
        )