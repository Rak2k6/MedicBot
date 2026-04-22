import re

LAB_KEYWORDS = {
    "glucose", "rbc", "wbc", "hemoglobin", "haemoglobin", "protein", "urine", 
    "stool", "bilirubin", "creatinine", "cholesterol", "triglyceride", "platelet", 
    "tsh", "t3", "t4", "albumin", "globulin", "hba1c", "esr", "pcv", "mch", "mchc"
}

STRUCTURAL_LAB_SIGNALS = {
    "reference range", "biological reference", "test name", "method", "unit", "observed value"
}

def classify_document(text: str) -> str:
    """
    Classifies a medical document into 'lab', 'clinical', or 'radiology'.
    """
    if not text:
        return "clinical"
        
    text_lower = text.lower()

    # RADIOLOGY RULES
    # If it has radiology specific terms that usually signify an imaging report
    radiology_signals = ["impression:", "appears normal", "measures", "ultrasound", "mri", "ct scan", "x-ray", "radiograph"]
    if any(signal in text_lower for signal in radiology_signals) and "impression" in text_lower:
        return "radiology"
    elif "impression:" in text_lower or "\nimpression" in text_lower:
        # Strong radiology signal
        return "radiology"
        
    # LAB RULES
    # Count lab keywords
    keyword_matches = sum(1 for kw in LAB_KEYWORDS if kw in text_lower)
    
    # Check for structural signals
    has_structural_signal = any(sig in text_lower for sig in STRUCTURAL_LAB_SIGNALS)
    
    # Requirement: >= 2 + structural signals
    if keyword_matches >= 2 and has_structural_signal:
        return "lab"
    elif keyword_matches >= 5:
        # High confidence lab even without strict structure header
        return "lab"
        
    # CLINICAL RULES (Fallback)
    return "clinical"
