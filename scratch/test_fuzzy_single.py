import difflib

def is_same_person_fuzzy(a1_dni, a1_name, a2_dni, a2_name):
    if a1_dni and a2_dni and a1_dni == a2_dni:
        return True
    
    if a1_name and a2_name:
        n1 = a1_name.lower().strip()
        n2 = a2_name.lower().strip()
        
        if n1 == n2:
            return True
        
        ratio = difflib.SequenceMatcher(None, n1, n2).ratio()
        if ratio > 0.85:
            return True
            
        set1 = set(n1.split())
        set2 = set(n2.split())
        
        # Exact match of at least 2 words
        if len(set1) > 1 and len(set2) > 1 and len(set1.intersection(set2)) >= 2:
            return True
            
        # Single word match (e.g. "SANDOVAL" vs "LAURA SONDOVAL URGUIA")
        if len(set1) == 1 or len(set2) == 1:
            single_word = list(set1)[0] if len(set1) == 1 else list(set2)[0]
            other_words = set2 if len(set1) == 1 else set1
            # Check if the single word is highly similar to any word in the full name
            for w in other_words:
                if difflib.SequenceMatcher(None, single_word, w).ratio() > 0.80:
                    return True
            
    return False

print("Test 1:", is_same_person_fuzzy(None, "LAURA SONDOVAL URGUIA", None, "SANDOVAL")) # Should be True
