import re

def clean_text(text: str) -> str:
    """
    Cleans raw OCR text by converting to lowercase, removing unnecessary symbols,
    and fixing basic OCR errors.
    """
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Remove unnecessary symbols (*, _)
    text = re.sub(r'[*_\\]+', ' ', text)
    
    # Reduce multiple dots to a single space if they seem to be fillers, 
    # but preserve decimals like 13.5
    text = re.sub(r'\.{2,}', ' ', text)
    
    # Normalize spacing
    text = re.sub(r' +', ' ', text)
    
    # Fix basic OCR errors
    ocr_fixes = {
        "hae moglobin": "haemoglobin",
        "sp o2": "spo2"
    }
    for wrong, right in ocr_fixes.items():
        text = text.replace(wrong, right)
        
    return text.strip()
