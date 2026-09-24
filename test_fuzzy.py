import difflib

def is_same_person_fuzzy(a1_dni, a1_name, a2_dni, a2_name):
    if a1_dni and a2_dni and a1_dni == a2_dni:
        return True
    
    if a1_name and a2_name:
        n1 = a1_name.lower().strip()
        n2 = a2_name.lower().strip()
        
        if n1 == n2:
            return True
        
        # Levenshtein ratio
        ratio = difflib.SequenceMatcher(None, n1, n2).ratio()
        if ratio > 0.85:
            return True
            
        # Token overlap
        set1 = set(n1.split())
        set2 = set(n2.split())
        if set1 and set2 and len(set1.intersection(set2)) >= 2:
            # At least two names match exactly (e.g. "LAURA SANDOVAL" and "LAURA SONDOVAL URGUIA")
            return True
            
    return False

print(is_same_person_fuzzy(None, "LAURA SONDOVAL URGUIA", None, "LAURA SANDOVAL URGUIA")) # Should be True
