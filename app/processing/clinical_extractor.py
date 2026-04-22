import re

def extract_clinical_data(text: str) -> dict:
    """
    Safely extracts predefined high-confidence clinical data elements
    without using complex spatial parsing.
    """
    result = {
        "vitals": {},
        "lab_tests": []
    }
    
    if not text:
        return result
        
    text_lower = text.lower()
    
    # 1. Vitals Extraction
    # BP: e.g., 120/80 mmHg
    bp_match = re.search(r'\b(bp|blood pressure)[:\-\s]*(\d{2,3})\s*/\s*(\d{2,3})\b', text_lower)
    if bp_match:
        result["vitals"]["bp_systolic"] = bp_match.group(2)
        result["vitals"]["bp_diastolic"] = bp_match.group(3)
        
    # Pulse/Heart Rate
    pulse_match = re.search(r'\b(pulse|hr|heart rate)[:\-\s]*(\d{2,3})\s*(bpm|beats)?', text_lower)
    if pulse_match:
        result["vitals"]["pulse"] = pulse_match.group(2)
        
    # SPO2
    spo2_match = re.search(r'\b(spo2|saturation)[:\-\s]*(\d{2,3})\s*%', text_lower)
    if spo2_match:
        result["vitals"]["spo2"] = spo2_match.group(2)
        
    # Temp
    temp_match = re.search(r'\b(temp|temperature)[:\-\s]*(\d{2,3}(\.\d)?)\s*(f|c)', text_lower)
    if temp_match:
        result["vitals"]["temperature"] = temp_match.group(2)
        result["vitals"]["temperature_unit"] = temp_match.group(4).upper()


    # 2. Simple High-confidence Lab Extraction (Regex based)
    
    # Hemoglobin
    hb_match = re.search(r'\b(hb|hemoglobin|haemoglobin)[:\-\s]*(\d{1,2}\.\d)\s*(g/dl|g/l)', text_lower)
    if hb_match:
        result["lab_tests"].append({
            "test_name": "Hemoglobin",
            "value": hb_match.group(2),
            "unit": "g/dL",
            "confidence": 0.8
        })
        
    # TLC / WBC
    tlc_match = re.search(r'\b(tlc|wbc)[:\-\s]*(\d{1,3}(\.\d)?(,\d{3})?)\s*(cells/cumm|cumm|/cumm|x10\^3/ul)', text_lower)
    if tlc_match:
        result["lab_tests"].append({
            "test_name": "TLC",
            "value": tlc_match.group(2).replace(",", ""),
            "unit": tlc_match.group(5),
            "confidence": 0.8
        })
        
    # TSH
    tsh_match = re.search(r'\b(tsh)[:\-\s]*(\d{1,3}\.\d+)\s*(uIU/ml|miu/l|uI/ml)', text_lower)
    if tsh_match:
        result["lab_tests"].append({
            "test_name": "TSH",
            "value": tsh_match.group(2),
            "unit": tsh_match.group(3).replace("i", "I"),
            "confidence": 0.8
        })
        
    # 3. Qualitative Extraction
    # Handle single standalone negative lines if preceded by certain contexts
    # Since this is a simple fallback, we just look for 'negative' next to known terms
    qualitative_terms = ["hiv", "hbsag", "hcv", "vdrl", "covid", "dengue", "malaria"]
    for term in qualitative_terms:
         # look for term followed by negative, nil, absent
         q_match = re.search(rf'\b({term})[\s\:\-]+(negative|nil|absent)\b', text_lower)
         if q_match:
             result["lab_tests"].append({
                 "test_name": term.upper(),
                 "value": q_match.group(2),
                 "unit": None,
                 "confidence": 0.8
             })

    return result
