from app.preprocessing.text_prep import preprocess
from app.preprocessing.mapper import extract_term_prefix
from app.preprocessing.extractor import extract_value_unit

def process_text(raw_text: str) -> dict:
    """
    Main pipeline to process messy OCR text into structured JSON (dictionary).
    """
    # 1. Preprocess using the rule-based unified engine
    lines = preprocess(raw_text)
    
    # Print output of preprocess
    print("--- Preprocessed Lines ---")
    for line in lines:
        print(line)
    print("--------------------------")
    
    # 2. Map & Extract
    structured_data = {}
    
    for line in lines:
        term, remaining = extract_term_prefix(line)
        
        # Noise Removal: If we didn't identify a medical term, ignore this line
        if not term:
            continue
            
        value_unit = extract_value_unit(remaining)
        
        # If extraction was successful, add it to our resultant data
        if value_unit is not None:
            structured_data[term] = value_unit
            
    # don't remove raw text from output, needed for testing
    structured_data["raw_text"] = raw_text
            
    return structured_data
