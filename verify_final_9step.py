import sys
import os
import json
import logging

# Add app directory to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'app'))

from app.processing.layout_parser import LayoutParser

# Setup basic logging
logging.basicConfig(level=logging.INFO)

def test_9step_pipeline():
    parser = LayoutParser()
    
    # Mock tokens for a multi-column page
    # Column 1 (0-400), Column 2 (500-900)
    tokens = [
        # Col 1: Hemoglobin
        {"text": "Hemoglobin", "x": 50, "y": 200, "w": 100, "h": 20, "conf": 0.9},
        {"text": "14.5", "x": 200, "y": 200, "w": 50, "h": 20, "conf": 0.95},
        {"text": "g/dL", "x": 270, "y": 200, "w": 40, "h": 20, "conf": 0.9},
        {"text": "12.0 - 15.0", "x": 330, "y": 200, "w": 80, "h": 20, "conf": 0.8},
        
        # Col 2: RBC Count (Same Y as Hemoglobin but different column)
        {"text": "RBC Count", "x": 550, "y": 200, "w": 100, "h": 20, "conf": 0.9},
        {"text": "4.8", "x": 750, "y": 200, "w": 50, "h": 20, "conf": 0.95},
        {"text": "millions/cumm", "x": 820, "y": 200, "w": 100, "h": 20, "conf": 0.9},
        
        # Qualitative Test: Urine Protein (Disjointed)
        {"text": "Urine Protein", "x": 50, "y": 400, "w": 120, "h": 20, "conf": 0.9},
        {"text": "Negative", "x": 250, "y": 415, "w": 80, "h": 20, "conf": 0.99}, # Drifted by 15px (0.75 dyn_h)
        
        # Physical Examination Attribute
        {"text": "Color", "x": 550, "y": 400, "w": 50, "h": 20, "conf": 0.9},
        {"text": "Straw Yellow", "x": 750, "y": 400, "w": 100, "h": 20, "conf": 0.9},
        
        # Garbage: SID in header (Penalty test)
        {"text": "SID: 987654", "x": 400, "y": 20, "w": 100, "h": 20, "conf": 0.9}
    ]
    
    raw_mock = []
    for t in tokens:
        raw_mock.append({
            "box": [[t["x"], t["y"]], [t["x"]+t["w"], t["y"]], [t["x"]+t["w"], t["y"]+t["h"]], [t["x"], t["y"]+t["h"]]],
            "text": t["text"],
            "confidence": t["conf"]
        })
        
    unified = parser.convert_to_unified_format(raw_mock, "easyocr")
    print("\nUnified Tokens (with Zones/Admin):")
    for t in unified:
        print(f"Text: {t['text']:15} Zone: {t['in_zone']:8} Admin: {t['is_admin']}")
        
    results = parser.parse_document_spatial(unified)
    
    print("\n9-Step Pipeline Extraction Results:")
    for r in results:
        print(f"Test: {r['test_name']:20} Value: {r['value']:10} Conf: {r['confidence']}")
    
    tests_found = [r["test_name"] for r in results]
    
    # Assertions
    assert any("HEMOGLOBIN" in t.upper() for t in tests_found), f"Hemoglobin missing, found: {tests_found}"
    assert any("RED BLOOD CELLS" in t.upper() for t in tests_found), f"RBC missing, found: {tests_found}"
    # Note: Urine Protein normalizes to URINE ALBUMIN based on current test_names.json grouping
    assert any("URINE ALBUMIN" in t.upper() for t in tests_found), f"Urine Protein missing/incorrect, found: {tests_found}"
    assert any("COLOR" in t.upper() for t in tests_found), f"Color missing, found: {tests_found}"
    assert not any("SID" in t.upper() for t in tests_found), f"SID found: {tests_found}"
    
    print("\n--- ALL PIPELINE TESTS PASSED ---")

if __name__ == "__main__":
    test_9step_pipeline()
