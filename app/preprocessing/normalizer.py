import re

def normalize_separators(text: str) -> str:
    """
    Converts all separators like `|`, `;`, tabs, and multiple spaces into newlines
    to isolate medical parameters.
    """
    if not text:
        return ""
        
    # Replace common horizontal separators with newline
    text = re.sub(r'[\|;\t]', '\n', text)
    
    # We can also handle specific separator cases like " : " if we want,
    # but the prompt specifically mentioned |, ;, tabs, and multiple spaces.
    # Replace multiple spaces (e.g. 3 or more) with newline as well since it 
    # often delineates columns in OCR.
    text = re.sub(r' {3,}', '\n', text)
    
    # Clean up empty lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)
