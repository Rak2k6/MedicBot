import re
import logging
from typing import List, Optional

# Configure logging (null handler to avoid unconfigured logging warnings)
logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """
    Normalizes whitespace and newlines.
    """
    if not text:
        return ""
        
    text = text.replace('\r', '')
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines).strip()
    return text

def is_admin_or_branding_noise(line: str, custom_keywords: Optional[List[str]] = None) -> bool:
    """
    Checks if a line contains administrative or branding content.
    """
    # 1. Keyword-based removal
    default_keywords = [
        "hospital", "laboratory", "clinic", "diagnostics", "scans", "imaging", "centre", "center", 
        "pvt ltd", "ltd", "limited", "address", "addr", "ph:", "phone", "mobile", "tel:", "contact", 
        "email", "website", "www.", ".com", ".org", ".net", "road", "street", "lane", "nagar", "city", 
        "pincode", "pin:", "page ", "page:", "printed on", "visit date", "visitdate", "report date", 
        "collected on", "received on", "registered on", "dr.", "doctor", "consultant", "ref by", 
        "referred by", "patient name", "name:", "age", "sex", "gender", "uhid", "bill no", 
        "sample id", "accession", "reg no", "barcode", "end of report", "accredited", "nabl", "iso", 
        "hallmark", "quality", "customer care", "helpline", "gst", "tin", "cst", "department of",
        "signature", "technologist", "pathologist", "radiologist", "checked by", "verified by",
        "disclaimer", "method:", "specimen:", "sample type", "interpretation", "clinical notes",
        "comments:", "reference range", "bio-ref", "test value unit", "test name", "observed value"
    ]
    
    keywords = default_keywords
    if custom_keywords:
        keywords.extend(k.lower() for k in custom_keywords)
        
    line_lower = line.lower()
    
    for kw in keywords:
        if kw in line_lower:
            # Handle generic 'of' carefully
            if kw == "of":
                 # Strict check for page numbers
                 if re.search(r'\bpage\s+\d+\s+of\s+\d+', line_lower):
                     return True
                 continue
            return True

    # 2. Regex-based removal
    
    # Phone numbers
    if re.search(r'(\+91|044|0\d{2,4})[\s-]?\d{6,10}', line):
        return True
    
    # Emails
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', line):
        return True
        
    # URLs
    if re.search(r'www\.|http:|https:', line_lower):
        return True
        
    # Pincodes
    if re.search(r'\b\d{6}\b', line) and ("chennai" in line_lower or "tamil" in line_lower or "road" in line_lower):
        return True
        
    return False

# Medical Indicators
# 1. Strong Result Terms (findings) - Keep these even if no number is present
strong_result_terms = [
    'positive', 'negative', 'detected', 'not detected', 'seen', 'absent', 'present', 
    'reactive', 'non-reactive', 'trace', 'nil', 'growth', 'no growth', 'isolated', 
    'sensitive', 'resistant', 'intermediate', 'normal', 'abnormal', 'high', 'low'
]

# 2. Context Terms - Require a number OR be a known test name (Stage-2 relaxation)
context_terms = [
    'count', 'total', 'direct', 'indirect', 'volume', 'size', 'measure', 'echo', 
    'grade', 'stage', 'level', 'range', 'reference', 'result', 'observed', 'value',
    'method', 'test', 'specimen', 'sample',
    "abnormal", "scan", "investigation", "method", "result", "reference", "units",
    "stool", "urine", "blood", "serum", "plasma", "culture", "microscopy",
    "bilirubin", "protein", "albumin", "globulin", "sugar", "glucose", "ketone",
    "pus", "cells", "epithelial", "casts", "crystals", "bacteria", "yeast",
    "rbc", "wbc", "platelet", "hemoglobin", "haemoglobin", "neutrophil", "lymphocyte",
    "eosinophil", "monocyte", "basophil", "esr", "pcv", "mcv", "mch", "mchc"
]

def is_medical_result(line: str) -> bool:
    """
    Determines if a line is likely a medical result (value + unit or qualitative).
    Stage-2: Also preserves lines that look like test names or headers.
    """
    if not line or len(line.strip()) < 3:
        return False
        
    line_lower = line.lower()
    
    # Check for Strong Result Terms (Qualitative)
    for term in strong_result_terms:
        # Use word boundary to avoid partial matches
        if re.search(r'\b' + re.escape(term) + r'\b', line_lower):
            return True

    # Check for Medical Context Terms (Test Names) - Stage-2 Addition
    # If the line contains a known medical term, we keep it to allow the parser to decide.
    for term in context_terms:
        if term in line_lower:
             return True

    # Check for Digit Requirement (Validation for lines without keywords)
    has_digit = any(char.isdigit() for char in line)

    # 3. Units - Require number + unit proximity
    units = [
        'g/dl', 'mg/dl', 'mcg/dl', 'u/l', 'iu/l', 'mmol/l', 'meq/l', 'cells/cumm', '/cmm', '/cumm',
        'million/cmm', 'lakhs/cumm', '%', 'fl', 'pg', 'g/l', 'ng/ml', 'microl', 'ratio', 
        'mm/hr', 'mmhg', 'bpm', 's/co', 'index', 'copies/ml', 'cm', 'mm', 'cc', 'vol', 'ml',
        'count', '/hpf', '/lpf', '/ul', 'x10^3/ul', 'million/ul', 'x10^6/ul'
    ]
    
    # Regex: Digit + optional gap + Unit
    units_pattern = r'\d\s*(' + '|'.join(re.escape(u) for u in units) + r')(?!\w)'
    
    if re.search(units_pattern, line_lower):
        return True
        
    # 4. Check for likely headers or test names (Multi-line support)
    # If it survived the noise filter, and it has a reasonable amount of text,
    # and is either title-case, upper-case, or has test-name-like punctuation
    alpha_count = sum(c.isalpha() for c in line)
    if alpha_count > 3 and len(line) < 60:
         # If it's all uppercase (like many OCR headers) or Title Case
         if line.isupper() or line.istitle():
             return True
         # If it has typical test name characters
         if '-' in line or '(' in line or '/' in line:
             return True
             
    # If it has a digit but no unit/keyword, assume it's noise unless it looks very specific?
    # For now, safe to filter out standalone numbers without context.
    return False


def clean_lab_report(raw_text: str, custom_blocklist: Optional[List[str]] = None) -> str:
    """
    Cleans raw lab report text to isolate medical results.
    """
    if not raw_text:
        # Don't raise error, return empty string
        return ""
        
    normalized_text = normalize_text(raw_text)
    cleaned_lines = []
    
    for line in normalized_text.split('\n'):
        if not line.strip():
            continue
            
        if is_admin_or_branding_noise(line, custom_blocklist):
            continue
            
        if is_medical_result(line):
            cleaned_lines.append(line)
            
    result = '\n'.join(cleaned_lines)
    
    if not result:
        # Return raw text if cleaning removed everything? 
        # No, better to return empty than garbage.
        # But if raw_text was huge and result is empty, something is wrong.
        if len(raw_text) > 100:
             logger.warning("Cleaned output is empty despite large input. Filter might be too strict.")
        return ""
        
    return result
