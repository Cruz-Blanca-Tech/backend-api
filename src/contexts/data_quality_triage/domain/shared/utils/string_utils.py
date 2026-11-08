import difflib
import re
import unicodedata


def name_match_key(value) -> str:
    """Clave para COMPARAR nombres (no para guardar): sin tildes ni ñ, en
    minúsculas, sin puntuación y con espacios simples. Misma regla que
    `beneficiary_fuzzy_matcher.normalize_name` (NFKD a ASCII), para que
    «NÚÑEZ» y «NUNEZ» se comparen como iguales en todo el triaje (D9)."""
    if not value:
        return ""
    ascii_only = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii", "ignore")
    ascii_only = re.sub(r"[^a-z0-9 ]+", " ", ascii_only.lower())
    return re.sub(r"\s+", " ", ascii_only).strip()


def calculate_similarity(name1: str, name2: str) -> float:
    """Calcula similitud de dos nombres basándose en difflib. Valores de 0.0 a 1.0"""
    if not name1 or not name2:
        return 0.0
    return difflib.SequenceMatcher(None, name1.strip(), name2.strip()).ratio()
