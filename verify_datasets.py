import os
import sys
import json

# Add 'app' to sys.path
sys.path.append(os.path.abspath("app"))

from app.processing.pdf_extract import extract_pdf_text

def test_datasets():
    datasets_dir = r"e:/Rakesh/Rak/projects/mediQ Bot/datasets"
    
    if not os.path.exists(datasets_dir):
        print(f"Directory not found: {datasets_dir}")
        return
        
    pdf_files = [f for f in os.listdir(datasets_dir) if f.lower().endswith(".pdf")]
    
    print(f"Found {len(pdf_files)} PDFs in {datasets_dir}\n")
    
    summary = {}
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(datasets_dir, pdf_file)
        print(f"==================================================")
        print(f"Processing: {pdf_file}")
        
        result = extract_pdf_text(pdf_path)
        
        if result:
            tests = result.get('lab_tests', {})
            num_tests = len(tests)
            
            numeric_count = sum(1 for v in tests.values() if v.get('type') == 'numeric')
            qualitative_count = sum(1 for v in tests.values() if v.get('type') == 'qualitative')
            
            print(f"  Status: SUCCESS")
            print(f"  Total Tests Found: {num_tests}")
            print(f"  - Numeric: {numeric_count}")
            print(f"  - Qualitative: {qualitative_count}")
            
            # Print specifically which ones were found to eyeball quality
            if num_tests > 0:
                print("\n  Sample Tests:")
                for k, v in list(tests.items())[:8]:
                    if v.get('type') == 'numeric':
                        print(f"    - {k}: {v.get('value')} {v.get('unit')} (Range: {v.get('reference_range')})")
                    else:
                        print(f"    - {k}: {v.get('value')} (Specimen: {v.get('specimen')})")
            else:
                print("\n  [DEBUG] Extracted Text (first 500 chars):")
                print("  " + result.get('extracted_text', '')[:500].replace('\n', '\n  '))
                        
            summary[pdf_file] = {
                "total": num_tests,
                "numeric": numeric_count,
                "qualitative": qualitative_count
            }
        else:
            print(f"  Status: FAILED")
            summary[pdf_file] = {"total": 0, "status": "failed"}
            
        print(f"==================================================\n")
        
    print("\nSUMMARY:")
    for file, data in summary.items():
        if data.get("status") == "failed":
            print(f"- {file}: FAILED")
        else:
            print(f"- {file}: {data['total']} tests ({data['numeric']} Num, {data['qualitative']} Qual)")

if __name__ == "__main__":
    test_datasets()
