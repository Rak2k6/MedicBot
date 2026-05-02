import re
from app.preprocessing.mapper import SORTED_KEYS

# Create an optimized regex to dynamically split lines containing multiple parameters.
# Match a space, followed by one of the known medical terms.
# Using lookahead so we don't consume the term itself.
TERM_PATTERN = r'\s+(?=(?:' + '|'.join(map(re.escape, SORTED_KEYS)) + r')\b)'
SPLIT_REGEX = re.compile(TERM_PATTERN, re.IGNORECASE)

def segment_lines(text: str) -> list[str]:
    """
    Splits text into lines, and further splits lines that contain multiple parameters.
    """
    if not text:
        return []
        
    lines = text.split('\n')
    segmented_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Split on known terms that appear mid-line preceded by space
        parts = SPLIT_REGEX.split(line)
        for part in parts:
            part = part.strip()
            if part:
                segmented_lines.append(part)
                
    return segmented_lines
