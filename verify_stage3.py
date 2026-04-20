import json
import os
import sys
import logging

# Add 'app' to sys.path to simulate running from inside app (for config imports)
sys.path.append(os.path.abspath("app"))

from app.processing.pdf_extract import extract_pdf_text

# Configure logging to see our new logs
logging.basicConfig(level=logging.INFO)

# Path to the dataset file
pdf_path = r"e:/Rakesh/Rak/projects/mediQ Bot/datasets/Aarthi scans kannan.pdf"

if not os.path.exists(pdf_path):
    print(f"File not found: {pdf_path}")
else:
    print(f"Processing {pdf_path}...")
    result = extract_pdf_text(pdf_path)
    
    if result:
        print("\n--- Extraction Success ---")
        metadata = result.get('metadata', {})
        print(f"Tests Found: {len(result.get('lab_tests', {}))}")
        print(f"OCR Stage: {metadata.get('ocr_stage', 'Unknown')}")
        print(f"Report Type: {metadata.get('report_type', 'Unknown')}")
        print(f"Qualitative Rules Applied: {metadata.get('qualitative_rules_applied', False)}")
        
        # Save output to inspect
        output_file = "stage3_output.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Full output saved to {output_file}")
        
        # Print qualitative tests specifically
        print("\nQualitative Tests Found:")
        qual_count = 0
        tests = result.get('lab_tests', {})
        for k, v in tests.items():
            if v.get('type') == 'qualitative':
                print(f"{k}: {v.get('value')} (Conf: {v.get('confidence')}, Specimen: {v.get('specimen')})")
                qual_count += 1
        
        if qual_count == 0:
            print("No qualitative tests found.")
            
        print("\nSample Numeric Tests (Regression Check):")
        num_count = 0
        for k, v in list(tests.items())[:5]:
             if v.get('type') == 'numeric':
                print(f"{k}: {v.get('value')} {v.get('unit')}")
                num_count += 1
    else:
        print("Extraction Failed.")
