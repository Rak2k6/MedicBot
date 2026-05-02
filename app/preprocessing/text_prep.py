import re

# 1. OCR Error Correction Mapping
OCR_FIXES = {
    "mev": "mcv",
    "plat": "platelets",
    "tlc": "wbc",
    "resp": "respiratory rate",
    "hb": "hemoglobin",
    "hgb": "hemoglobin"
}

# 2. Section Headers to Filter
SECTIONS_TO_REMOVE = [
    "chief complaints",
    "present illness",
    "past history",
    "diagnosis",
    "examination"
]

# 3. Medical Keywords for Segmentation
MEDICAL_KEYWORDS = [
    "weight", "bp", "systolic", "diastolic", "pulse", "spo2", 
    "respiratory rate", "temperature", "hb", "hgb", "hemoglobin", 
    "wbc", "rbc", "platelets", "esr", "tsh", "glucose",
    "systolic bp", "diastolic bp", "mcv"
]

def clean_text(text: str) -> str:
    """
    1. Text Cleaning:
    - Convert to lowercase
    - Replace newline characters with space
    - Remove extra whitespace
    - Remove unwanted symbols (e.g., *, extra punctuation)
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace newlines with space
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    # Remove unwanted symbols and extra punctuation
    # We keep letters, numbers, spaces, and . : / % - , | ( )
    text = re.sub(r'[^\w\s.:/%\|, ()\-]', ' ', text)
    
    # Normalize extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def apply_ocr_fixes(text: str) -> str:
    """
    2. OCR Error Correction:
    Apply a mapping dictionary to fix common OCR mistakes.
    """
    for wrong, right in OCR_FIXES.items():
        # Use word boundaries to ensure we only replace whole words
        text = re.sub(rf'\b{wrong}\b', right, text)
    return text

def normalize_separators(text: str) -> str:
    """
    3. Separator Normalization:
    - Convert separators like |, , into newline characters
    - Normalize spacing around : (key : value)
    - Ensure uniform spacing across the text
    """
    # Convert | and , to \n
    text = re.sub(r'[|,]', '\n', text)
    
    # Normalize spacing around :
    text = re.sub(r'\s*:\s*', ' : ', text)
    
    # Ensure uniform spacing (single space) within lines
    lines = []
    for line in text.split('\n'):
        clean_line = re.sub(r'\s+', ' ', line).strip()
        if clean_line:
            lines.append(clean_line)
            
    return '\n'.join(lines)

def remove_sections(text: str) -> str:
    """
    4. Section Filtering (CRITICAL):
    Remove entire sections that are not structured medical data.
    Everything under headers like 'Chief Complaints' is excluded.
    """
    # We look for the first occurrence of any forbidden section and truncate everything after it.
    first_occurrence = len(text)
    
    for section in SECTIONS_TO_REMOVE:
        # Use case-insensitive search just in case, though clean_text already lowercased it
        match = re.search(rf'\b{section}\b', text, re.IGNORECASE)
        if match and match.start() < first_occurrence:
            first_occurrence = match.start()
            
    return text[:first_occurrence].strip()

def segment_text(text: str) -> list[str]:
    """
    5. Keyword-Based Segmentation (CORE LOGIC):
    Split text based on keyword occurrences.
    """
    # Sort keywords by length descending to match longer phrases first (e.g., 'systolic bp' before 'bp')
    sorted_keywords = sorted(MEDICAL_KEYWORDS, key=len, reverse=True)
    
    # Create a regex pattern for all keywords
    pattern = r'\b(?:' + '|'.join(map(re.escape, sorted_keywords)) + r')\b'
    
    # We will split the text manually to keep the keyword with the following value
    # finditer gives us the positions of all keywords
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    
    if not matches:
        # If no keywords found, return the lines as is
        return [line.strip() for line in text.split('\n') if line.strip()]
    
    segments = []
    # If there's text before the first keyword, we might want to capture it if it looks like a pair
    # but the instructions suggest segments should ideally represent a parameter.
    # However, some text might be between keywords.
    
    for i in range(len(matches)):
        start = matches[i].start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        
        segment = text[start:end].strip()
        
        # Further clean segment: remove trailing separators like \n or , that might have stayed
        segment = segment.replace('\n', ' ').strip()
        if segment:
            segments.append(segment)
            
    return segments

def split_inline_segments(segments: list[str]) -> list[str]:
    """
    6. Inline Segmentation (NEW):
    - Split segments containing parentheses ()
    - Detect multiple key-value pairs in a single line
    - Clean and normalize separators to ':'
    """
    final_segments = []
    
    # Pre-calculate regex pattern for keyword splitting
    sorted_keywords = sorted(MEDICAL_KEYWORDS, key=len, reverse=True)
    keyword_pattern = r'\b(?:' + '|'.join(map(re.escape, sorted_keywords)) + r')\b'

    for segment in segments:
        # 1. Split by parentheses
        # Example: "hb- 9.8 (mcv- 76.5)" -> ["hb- 9.8", "mcv- 76.5"]
        parts = re.split(r'[()]', segment)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            # 2. Detect multiple key-value pairs within this part
            # We use the same logic as segment_text but on this sub-segment
            matches = list(re.finditer(keyword_pattern, part, re.IGNORECASE))
            
            if len(matches) > 1:
                # Multiple keywords found, split them
                for i in range(len(matches)):
                    start = matches[i].start()
                    end = matches[i+1].start() if i+1 < len(matches) else len(part)
                    sub_segment = part[start:end].strip()
                    if sub_segment:
                        final_segments.append(sub_segment)
            else:
                # Single or no keyword, add as is
                final_segments.append(part)
    
    # 3. Clean each segment and normalize separators like '-' to ':'
    cleaned_final = []
    for s in final_segments:
        # Replace common separators with ':' if not already present
        if ':' not in s:
            # Replace '-' with ':' if it looks like a separator (word-space-digit or word-digit)
            s = re.sub(r'(\b\w+)\s*[-]\s*(\d)', r'\1 : \2', s)
            # If still no ':', and it starts with a keyword, try to insert one after the keyword
            if ':' not in s:
                kw_match = re.search(keyword_pattern, s, re.IGNORECASE)
                if kw_match:
                    kw_end = kw_match.end()
                    # If there's a value after the keyword but no separator, insert ':'
                    if re.search(r'\d', s[kw_end:]):
                        # Insert ':' after keyword
                        s = s[:kw_end] + " : " + s[kw_end:].strip()

        # Final cleanup: normalize spacing
        s = re.sub(r'\s*:\s*', ' : ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        
        # Ignore very short fragments (e.g., just a single letter or number without context)
        if len(s) > 2:
            cleaned_final.append(s)
            
    return cleaned_final

def preprocess(text: str) -> list[str]:
    """
    Transform raw OCR text into clean, structured segments.
    """
    # Step 1: Clean Text
    text = clean_text(text)
    
    # Step 2: OCR Fixes
    text = apply_ocr_fixes(text)
    
    # Step 3: Normalize Separators
    text = normalize_separators(text)
    
    # Step 4: Remove Sections
    text = remove_sections(text)
    
    # Step 5: Segmentation
    segments = segment_text(text)
    
    # Step 6: Inline Segmentation (NEW)
    segments = split_inline_segments(segments)
    
    return segments
