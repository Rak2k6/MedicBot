import re

# Common variations of string values we might encounter
TEXT_VALUES = {"positive", "negative", "reactive", "non-reactive", 
               "present", "absent", 
               "a+", "a-", "b+", "b-", "ab+", "ab-", "o+", "o-"}

def extract_value_unit(text_remaining: str):
    """
    Given the remaining part of a line after removing the primary medical term,
    attempts to separate it into a numerical value and unit, or just a text value.
    Returns: dict {"value": 116, "unit": "bpm"} or string value (like "O+")
    or None if parsing fails.
    """
    if not text_remaining:
        return None
        
    text_remaining = text_remaining.strip()
    text_lower = text_remaining.lower()
    
    # 1. Check for text values (like O+, positive, etc.)
    for tv in TEXT_VALUES:
        if text_lower.startswith(tv) or text_lower == tv:
            val = text_remaining[:len(tv)].strip()
            # Standardize case for common text values
            if val.lower() in {"a+", "a-", "b+", "b-", "ab+", "ab-", "o+", "o-"}:
                return val.upper()
            return val.title()
            
    # 2. Extract numeric values and units
    # Look for number (int/float), optional spaces, optional unit
    match = re.search(r'([\d]+(?:\.\d+)?)\s*(.*)', text_remaining)
    if match:
        val_str = match.group(1)
        unit_str = match.group(2).strip()
        
        # Convert value to int or float
        if '.' in val_str:
            try:
                num = float(val_str)
            except ValueError:
                num = val_str
        else:
            try:
                num = int(val_str)
            except ValueError:
                num = val_str
                
        # Additional cleaning for unit
        if unit_str:
            # Remove trailing dots/chars that aren't part of unit
            unit_str = unit_str.strip('. ')
            
        result = {"value": num}
        if unit_str:
            result["unit"] = unit_str
            
        return result
        
    # If no numbers, return the string as text value
    if text_remaining:
        return text_remaining
    return None
