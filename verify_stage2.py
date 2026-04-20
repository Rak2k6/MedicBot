import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'app'))
from app.processing.pdf_extract import extract_pdf_text
import json
import os
import logging

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
        print(f"Tests Found: {len(result.get('lab_tests', {}))}")
        print(f"Stage 2 Pipeline Used: {result.get('metadata', {}).get('stage_2_pipeline', False)}")
        
        # Save output to inspect
        output_file = "stage2_output.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Full output saved to {output_file}")
        
        # Print a few tests
        print("\nSample Tests:")
        tests = result.get('lab_tests', {})
        for k, v in list(tests.items())[:5]:
            print(f"{k}: {v}")
    else:
        print("Extraction Failed.")
