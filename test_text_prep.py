from app.preprocessing import process_text
import json

raw_text = """haemoglobin 13.5 g/dl | blood group : O+
Pulse 116 SpO2 99
WBC 9000 RBC 4.5 Platelets 2.5 lakh
ABC Diagnostics Pvt Ltd"""

print("### Input Content ###")
print(raw_text)
print("\n### Structured Output ###")
result = process_text(raw_text)
print(json.dumps(result, indent=2))
