import re

def extract_radiology_data(text: str) -> dict:
    """
    Extracts specialized radiology information from a document, 
    such as organ-specific findings and the final impression.
    """
    result = {
        "findings": {},
        "impression": []
    }
    
    if not text:
        return result
        
    # 1. Organ Findings
    # Pattern: [organ] appears ... up to the next period or newline
    organs = ["liver", "kidney", "pancreas", "spleen", "prostate", "bladder", "gallbladder", "uterus", "ovary"]
    for organ in organs:
        # e.g., "Liver appears normal in size and echotexture."
        pattern = rf"\b({organ})\b\s+(appears|is|shows|measures)\b\s*(.*?)(?=\.|\n)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Reconstruct the sentence fragment
            finding_text = f"{match.group(1)} {match.group(2)} {match.group(3)}".strip()
            result["findings"][organ] = finding_text
            
    # 2. Impression Section
    # Extract lines after "Impression:", "Conclusion:", etc. until the end of the text
    # or until another major heading starts (simplistic approach: just get everything after)
    impression_match = re.search(r'(?i)\n\s*(?:impression|conclusion|diagnosis)\s*[:-]\s*\n?(.*)', text, re.DOTALL)
    if impression_match:
        impression_text = impression_match.group(1).strip()
        # Clean up impression text by making it a list of bullet points/sentences
        lines = [line.strip().lstrip('-').lstrip('*').strip() for line in impression_text.split('\n')]
        # Filter empty lines and administrative noise at the bottom
        for line in lines:
            if line and "dr." not in line.lower() and "signature" not in line.lower() and "end of report" not in line.lower():
                result["impression"].append(line)
            if "end of report" in line.lower():
                break
                
    return result
