"""
Búsqueda fuzzy de beneficiarios contra el maestro (persons).

Reemplaza la heurística anterior (primer token de first_name y last_name con
ILIKE al prefijo de 5 letras, sin acentos ni ranking). Problemas que resuelve:

- Acentos: "CHÁVEZ" (maestro) vs "CHAVEZ" (OCR) no coincidían en ILIKE.
- Tokens intermedios: solo se miraba el PRIMER token de cada campo; un segundo
  nombre o apellido (o un "CI" intermedio) rompía el match.
- Intercambio de columnas: nombres apellido-primero ("CHAVEZ VASQUEZ ANDRE")
  no se detectaban.
- Sin scoring: el candidato "primario" era la primera fila del LIMIT 3,
  sin orden por cercanía real.
- Sin dedupe: la misma persona podía salir varias veces con DNIs distintos.

Nueva estrategia:
1. Una sola consulta SQL amplia pero acotada: translate() para ignorar
   acentos y un OR que cubre N tokens (2 de nombre + 3 de apellido) contra
   AMBAS columnas (resiste el intercambio OCR de nombre/apellido).
2. Scoring en Python sobre nombres normalizados (NFKD, sin acentos,
   minúsculas): Jaccard de tokens del nombre completo (50%) + Jaccard de
   apellidos (30%, más discriminantes que los nombres propios) + proximidad
   de DNI con difflib (20%, solo para ranking).
3. Regla de negocio: se descartan candidatos que NO difieren del expediente
   (mismo DNI, o mismo DNI y mismo nombre) — eso es match MDM de identidad,
   no una sugerencia. El DNI cercano por sí solo NO dispara sugerencias
   (evita falsos positivos cuando los nombres no coinciden).
"""
import difflib
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# Mapa de acentos para translate() en SQL (PostgreSQL). Deben tener la misma
# longitud: se reemplaza carácter a carácter.
_ACCENT_SRC = "ÁÉÍÓÚÜÑáéíóúüñ"
_ACCENT_DST = "AEIOUUNaeiouun"

# Umbral de puntaje compuesto para aceptar un candidato como sugerencia.
_SCORE_THRESHOLD = 0.50
_WEIGHT_NAME = 0.5
_WEIGHT_SURNAME = 0.3
_WEIGHT_DNI = 0.2


@dataclass(frozen=True)
class FuzzyCandidate:
    first_name: str
    last_name: str
    dni: str
    score: float


def normalize_name(value: str) -> str:
    """Normaliza un nombre: minúsculas, sin acentos, sin puntuación y sin
    espacios repetidos. Es la forma canónica para comparar "igual de verdad"."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii", "ignore")
    ascii_only = re.sub(r"[^a-z0-9 ]+", " ", ascii_only.lower())
    return re.sub(r"\s+", " ", ascii_only).strip()


def _tokens(value: str) -> List[str]:
    return [t for t in normalize_name(value).split() if len(t) >= 2]


def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    if not a or not b:
        return 0.0
    set_a, set_b = set(a), set(b)
    return len(set_a & set_b) / len(set_a | set_b)


def _dni_similarity(a: Optional[str], b: Optional[str]) -> float:
    a = (a or "").strip()
    b = (b or "").strip()
    if not (a.isdigit() and b.isdigit()) or len(a) != len(b):
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def score_candidate(
    beneficiary_first: str,
    beneficiary_last: str,
    beneficiary_dni: Optional[str],
    candidate_first: str,
    candidate_last: str,
    candidate_dni: Optional[str],
) -> float:
    """Puntaje compuesto 0..1 para un candidato. 50% nombre completo,
    30% apellidos (más discriminantes), 20% cercanía de DNI."""
    b_all = _tokens(f"{beneficiary_first} {beneficiary_last}")
    b_surnames = _tokens(beneficiary_last)
    c_all = _tokens(f"{candidate_first} {candidate_last}")
    c_surnames = _tokens(candidate_last)

    name_sim = _jaccard(b_all, c_all)
    surname_sim = _jaccard(b_surnames, c_surnames)
    dni_sim = _dni_similarity(beneficiary_dni, candidate_dni)
    return _WEIGHT_NAME * name_sim + _WEIGHT_SURNAME * surname_sim + _WEIGHT_DNI * dni_sim


class BeneficiaryFuzzyMatcher:
    """Busca candidatos de beneficiario en `persons` cuando la OCR pudo mal
    leer el DNI o el nombre del expediente."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_suggestions(
        self,
        *,
        first_name: str,
        last_name: str,
        dni: Optional[str] = None,
        limit: int = 3,
    ) -> List[FuzzyCandidate]:
        b_first = first_name or ""
        b_last = last_name or ""
        b_dni = (dni or "").strip()

        given_tokens = [t.upper()[:5] for t in _tokens(b_first) if len(t) >= 3][:2]
        surname_tokens = [t.upper()[:5] for t in _tokens(b_last) if len(t) >= 3][:3]
        search_tokens = given_tokens + surname_tokens
        if not search_tokens:
            return []

        conds = " OR ".join(
            f"translate(last_name, :acc, :pln) ILIKE :p{i} "
            f"OR translate(first_name, :acc, :pln) ILIKE :p{i}"
            for i in range(len(search_tokens))
        )
        params: dict = {"acc": _ACCENT_SRC, "pln": _ACCENT_DST}
        params.update({f"p{i}": f"%{t}%" for i, t in enumerate(search_tokens)})

        sql = text(
            f"SELECT first_name, last_name, dni FROM persons "
            f"WHERE type = 'beneficiary' AND ({conds}) LIMIT 30"
        )
        result = await self._session.execute(sql, params)
        rows = result.fetchall()

        b_name_norm = normalize_name(f"{b_first} {b_last}")

        candidates: List[FuzzyCandidate] = []
        for row in rows:
            c_first = str(row[0] or "").strip()
            c_last = str(row[1] or "").strip()
            c_dni = str(row[2] or "").strip()

            # 1) DNI idéntico al expediente → match MDM por DNI, no sugerencia.
            if c_dni and b_dni and c_dni == b_dni:
                continue
            # 2) Mismo DNI Y mismo nombre → misma persona (match MDM de identidad).
            c_name_norm = normalize_name(f"{c_first} {c_last}")
            if c_dni and b_dni and c_dni == b_dni and c_name_norm == b_name_norm:
                continue

            score = score_candidate(b_first, b_last, b_dni, c_first, c_last, c_dni)
            if score < _SCORE_THRESHOLD:
                continue

            duplicate = next((c for c in candidates if c.dni == c_dni), None)
            if duplicate is not None:
                if score > duplicate.score:
                    candidates[candidates.index(duplicate)] = FuzzyCandidate(
                        first_name=c_first, last_name=c_last, dni=c_dni, score=score
                    )
                continue
            candidates.append(FuzzyCandidate(
                first_name=c_first, last_name=c_last, dni=c_dni, score=score
            ))

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:limit]