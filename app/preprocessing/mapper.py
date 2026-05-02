from app.rules.medic_dictionary import MEDIQ_DICT

# Create a flattened and reversed dictionary for fast O(1) lookup
# Format: { "hb": "hemoglobin", "hgb": "hemoglobin", ... }
FLAT_MEDIQ_DICT = {}
for standard_term, variations in MEDIQ_DICT.items():
    for variation in variations:
        FLAT_MEDIQ_DICT[variation.lower()] = standard_term

# Get a sorted list of keys by length (longest first)
SORTED_KEYS = sorted(FLAT_MEDIQ_DICT.keys(), key=len, reverse=True)

def standardize_term(term: str) -> str:
    """
    Standardizes a given medical parameter name to its consistent key.
    Returns the standardized term if found, else None.
    """
    if not term:
        return None
    
    term = term.strip().lower()
    return FLAT_MEDIQ_DICT.get(term)

def extract_term_prefix(line: str) -> tuple[str, str]:
    """
    Attempts to identify if a known medical term leads the line.
    If yes, returns (standardized_term, remaining_line).
    Matches the longest possible key.
    """
    if not line:
        return None, line
        
    line_lower = line.lower()
    
    for key in SORTED_KEYS:
        if line_lower.startswith(key):
            # Ensure it's a word boundary match
            if len(line_lower) > len(key) and line_lower[len(key)].isalpha():
                continue
                
            standardized = FLAT_MEDIQ_DICT[key]
            # Remaining line after the key
            remaining = line[len(key):].lstrip(' :-_=')
            return standardized, remaining
            
    return None, line

def find_terms_in_line(line: str) -> list[str]:
    """
    Finds all known medical term variations present in a line,
    returning a list of variation strings found.
    Helpful for identifying multi-parameter lines.
    """
    found = []
    line_lower = line.lower()
    for key in SORTED_KEYS:
        # Regex to exact match the word boundary
        import re
        if re.search(r'\b' + re.escape(key) + r'\b', line_lower):
            found.append(key)
    return found
