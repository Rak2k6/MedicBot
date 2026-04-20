import sys
import os
import json
import logging

# Add 'app' to sys.path
sys.path.append(os.path.abspath("app"))

try:
    from app.processing.pdf_extract import parse_lab_tests
except ImportError:
    from app.processing.pdf_extract import parse_lab_tests

# Configure logging
logging.basicConfig(level=logging.ERROR)

def run_test(name, text):
    print(f"\n--- Testing: {name} (Numeric/Stage-1 Regression) ---")
    print(f"Input Text:\n{text}")
    
    results = parse_lab_tests(text, [])
    
    print("Extracted Results:")
    print(json.dumps(results, indent=2))
    
    # Validation Logic
    passed = True
    
    if name == "Haemoglobin":
        if results.get("haemoglobin", {}).get("value") != 13.5: passed = False
        if results.get("haemoglobin", {}).get("unit") != "gms%": passed = False
        
    if name == "Lipid Profile":
        if results.get("total_cholesterol", {}).get("value") != 180.0: passed = False
        if results.get("hdl_cholesterol", {}).get("value") != 45.0: passed = False
        if results.get("triglycerides", {}).get("value") != 150.0: passed = False

    if passed:
        print("✅ PASSED: Numeric Extraction Preserved")
    else:
        print("❌ FAILED: Numeric Regression Detected")

# Test Case 1: Simple Numeric (Stage-1)
hb_text = """
HAEMATOLOGY REPORT
Test Name Result Unit Reference Range
Haemoglobin : 13.5 gms% (13.0 - 17.0)
"""
run_test("Haemoglobin", hb_text)

# Test Case 2: Lipid Profile (Table-like, Numeric)
lipid_text = """
LIPID PROFILE
Total Cholesterol 180.0 mg/dl
HDL Cholesterol   45.0  mg/dl
LDL Cholesterol   100.0 mg/dl
Triglycerides     150.0 mg/dl
"""
run_test("Lipid Profile", lipid_text)
