import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
from processing.layout_parser import LayoutParser

def test_layout_parser():
    parser = LayoutParser(rules_path=os.path.join(os.path.dirname(__file__), 'app', 'rules', 'test_names.json'))
    
    # Mock tokens for a row with multiple entities
    # "Hemoglobin 13.5 g/dL Blood Group : O+"
    tokens = [
        {"text": "Hemoglobin", "x": 100, "y": 200, "w": 80, "h": 20},
        {"text": "13.5", "x": 190, "y": 200, "w": 40, "h": 20},
        {"text": "g/dL", "x": 240, "y": 200, "w": 40, "h": 20},
        {"text": "Blood Group : O+", "x": 400, "y": 200, "w": 150, "h": 20}
    ]
    
    print("Testing Row Parsing (Multiple Entities):")
    results = parser.parse_entities_from_row(tokens)
    print(json.dumps(results, indent=2))
    
    # Mock tokens for multiline merging
    # Row 1: "WBC Count"
    # Row 2: "9000 /µL"
    rows = [
        [{"text": "WBC", "x": 100, "y": 250, "w": 40, "h": 20}, {"text": "Count", "x": 145, "y": 250, "w": 50, "h": 20}],
        [{"text": "9000", "x": 100, "y": 275, "w": 40, "h": 20}, {"text": "/µL", "x": 150, "y": 275, "w": 40, "h": 20}]
    ]
    
    print("\nTesting Multiline Merging:")
    merged = parser.merge_multiline_rows(rows)
    for i, row in enumerate(merged):
        print(f"Row {i}: {' '.join(t['text'] for t in row)}")
    
    parsed_merged = parser.parse_entities_from_row(merged[0])
    print("Parsed Merged Row:")
    print(json.dumps(parsed_merged, indent=2))

if __name__ == "__main__":
    test_layout_parser()
