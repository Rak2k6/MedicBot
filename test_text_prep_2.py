from app.preprocessing.text_prep import preprocess

test_text = "Weight : 63.00 Systolic BP : 167.0 Diastolic BP : 90 Temperature : 97.5 *F Pulse : 116 min. SPO2 : 99 % RESP : 20 , Chief Complaints : c/o pain abdomen..."

lines = preprocess(test_text)
for line in lines:
    print(f"* {line}")
