import sys
import os
import json
import logging

# Add 'app' to sys.path
sys.path.append(os.path.abspath("app"))

try:
    from app.processing.pdf_extract import parse_lab_tests
except ImportError:
    # If running from root, app might be package
    from app.processing.pdf_extract import parse_lab_tests

# Configure logging
logging.basicConfig(level=logging.ERROR)

def run_test(name, text, section_context=None):
    print(f"\n--- Testing: {name} ---")
    print(f"Input Text:\n{text}")
    print(f"Section Context: {section_context}")
    
    # Simulate section detection logic by prepending section header if needed, 
    # but parse_lab_tests logic for section detection relies on lines.
    # So we'll just inject the section header into the text for the parser to find.
    
    full_text = text
    if section_context:
        full_text = f"{section_context}\n{text}"
        
    results = parse_lab_tests(full_text, [])
    
    print("Extracted Results:")
    print(json.dumps(results, indent=2))
    
    # Validation Logic
    passed = True
    if name == "Urine Routine":
        if results.get("albumin", {}).get("value") != "nil": passed = False
        if results.get("sugar", {}).get("value") != "nil": passed = False
        if results.get("pus_cells", {}).get("value") != "few": passed = False
        if results.get("epithelial_cells", {}).get("value") != "2_3": passed = False # Wait, 2-3 is numeric usually? No, parsers might see it as text if not pure number
        # Actually 2-3 is a range. My numeric parser handles ranges? 
        # Regex: Value (Range)
        # "Pus Cells 2-3 /hpf" -> Value=2-3? No, regex expects single number value.
        # "2-3" is not a float. So numeric parser skips it.
        # Does qualitative parser pick it up? 
        # "2-3" is not in qualitative_values.
        # So "2-3" should be SKIPPED by current logic. 
        # "Few" should be captured.
        
        if "color" in results: print("WARNING: 'Color' should probably be skipped as it's not in closed set"); passed = False

    if name == "Serology":
        if results.get("hiv_i_ii", {}).get("value") != "non_reactive": passed = False
        if results.get("hbsag", {}).get("value") != "negative": passed = False

    if passed:
        print("✅ PASSED")
    else:
        print("❌ FAILED")

# Test Case 1: Urine Routine (Standard)
urine_text = """
URINE ROUTINE EXAMINATION
Color : Pale Yellow
Appearance : Clear
Reaction : Acidic
Specific Gravity : 1.015
Albumin : Nil
Sugar : Nil
Microscopy:
Pus Cells : 2-3 /hpf
Epithelial Cells : Few /hpf
Casts : Absent
Crystals : Not Seen
"""
run_test("Urine Routine", urine_text)

# Test Case 2: Serology (Stand-alone tests)
serology_text = """
HIV I & II : Non Reactive
HBsAg : Negative
HCV : Reactive
VDRL : Non-Reactive
"""
run_test("Serology", serology_text)

# Test Case 3: Two-line binding check
two_line_text = """
URINE
Acetone
Absent
Bile Salts
Not Detected
"""
run_test("Two-Line Check", two_line_text)

