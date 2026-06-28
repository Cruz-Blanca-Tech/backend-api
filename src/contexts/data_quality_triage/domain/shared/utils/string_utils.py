import difflib

def calculate_similarity(name1: str, name2: str) -> float:
    """Calcula similitud de dos nombres basándose en difflib. Valores de 0.0 a 1.0"""
    if not name1 or not name2:
        return 0.0
    return difflib.SequenceMatcher(None, name1.strip(), name2.strip()).ratio()
