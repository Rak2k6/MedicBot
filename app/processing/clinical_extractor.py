import re

def extract_clinical_data(segments: list[str]) -> dict:
    """
    Safely extracts predefined high-confidence clinical data elements
    from preprocessed text segments.
    """
    result = {
        "vitals": {},
        "lab_tests": []
    }
    
    if not segments:
        return result
        
    # Iterate through each preprocessed segment
    for segment in segments:
        segment_lower = segment.lower()
        
        # 1. Vitals Extraction
        
        # BP: e.g., "blood pressure : 120/80"
        bp_match = re.search(r'\b(bp|blood pressure|systolic bp|diastolic bp)[:\-\s]*(\d{2,3})\s*/\s*(\d{2,3})\b', segment_lower)
        if bp_match:
            result["vitals"]["bp_systolic"] = bp_match.group(2)
            result["vitals"]["bp_diastolic"] = bp_match.group(3)
        elif "systolic" in segment_lower and re.search(r'(\d{2,3})', segment_lower):
            s_match = re.search(r'(\d{2,3})', segment_lower)
            if s_match:
                result["vitals"]["bp_systolic"] = s_match.group(1)
        elif "diastolic" in segment_lower and re.search(r'(\d{2,3})', segment_lower):
            d_match = re.search(r'(\d{2,3})', segment_lower)
            if d_match:
                result["vitals"]["bp_diastolic"] = d_match.group(1)
            
        # Pulse/Heart Rate: e.g., "pulse : 116"
        pulse_match = re.search(r'\b(pulse|hr|heart rate)[:\-\s]*(\d{2,3})\b', segment_lower)
        if pulse_match:
            result["vitals"]["pulse"] = pulse_match.group(2)
            
        # SPO2: e.g., "spo2 : 99 %"
        spo2_match = re.search(r'\b(spo2|saturation)[:\-\s]*(\d{1,3})\s*%?', segment_lower)
        if spo2_match:
            result["vitals"]["spo2"] = spo2_match.group(2)
            
        # Temp: e.g., "temperature : 97.5 f"
        temp_match = re.search(r'\b(temp|temperature)[:\-\s]*(\d{2,3}(\.\d)?)\s*(f|c)?', segment_lower)
        if temp_match:
            result["vitals"]["temperature"] = temp_match.group(2)
            if temp_match.group(4):
                result["vitals"]["temperature_unit"] = temp_match.group(4).upper()


        # 2. Lab Extraction (Regex based on standardized names)
        
        # Hemoglobin
        hb_match = re.search(r'\b(hb|hemoglobin|haemoglobin)[:\-\s]*(\d{1,2}(?:\.\d+)?)\b', segment_lower)
        if hb_match:
            result["lab_tests"].append({
                "test_name": "Hemoglobin",
                "value": hb_match.group(2),
                "unit": "g/dL", # Default unit
                "confidence": 0.9
            })
            
        # WBC / TLC
        tlc_match = re.search(r'\b(tlc|wbc|white blood cell)[:\-\s]*(\d{1,6}(?:\.\d+)?)\b', segment_lower)
        if tlc_match:
            result["lab_tests"].append({
                "test_name": "WBC",
                "value": tlc_match.group(2),
                "unit": "cells/cumm",
                "confidence": 0.9
            })
            
        # TSH
        tsh_match = re.search(r'\b(tsh)[:\-\s]*(\d{1,3}(?:\.\d+)?)\b', segment_lower)
        if tsh_match:
            result["lab_tests"].append({
                "test_name": "TSH",
                "value": tsh_match.group(2),
                "unit": "uIU/mL",
                "confidence": 0.9
            })
            
        # MCV
        mcv_match = re.search(r'\b(mcv)[:\-\s]*(\d{1,3}(?:\.\d+)?)\b', segment_lower)
        if mcv_match:
            result["lab_tests"].append({
                "test_name": "MCV",
                "value": mcv_match.group(2),
                "unit": "fL",
                "confidence": 0.9
            })

        # 3. Qualitative Extraction
        qualitative_terms = ["hiv", "hbsag", "hcv", "vdrl", "covid", "dengue", "malaria"]
        for term in qualitative_terms:
             if term in segment_lower:
                 q_match = re.search(rf'\b({term})[\s\:\-]+(negative|nil|absent|positive|reactive|non-reactive)\b', segment_lower)
                 if q_match:
                     result["lab_tests"].append({
                         "test_name": term.upper(),
                         "value": q_match.group(2),
                         "unit": None,
                         "confidence": 0.9
                     })

    return result
