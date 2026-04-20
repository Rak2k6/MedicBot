# TODO: Advance PDF Extraction for Real-World Use Cases

## Tasks
- [x] Update requirements.txt to include pytesseract and pillow for OCR support
- [x] Enhance pdf_extract.py function:
  - [x] Add imports for pytesseract, PIL, re, json, logging
  - [x] Modify extract_pdf_text to extract tables using pdfplumber
  - [x] Add OCR support for scanned PDFs using pytesseract
  - [x] Implement advanced parsing with regex patterns for common lab report formats
  - [x] Handle large PDFs, multiple pages, and extract metadata
  - [x] Add robust error handling and validation
  - [x] Modify return structure to include tables, OCR text, etc.
  - [x] Integrate Google Gemini AI as last resort if all other methods fail
- [x] Install new dependencies (note: httpx version conflict with python-telegram-bot)
- [ ] Test with sample PDFs
- [ ] Update handlers.py if needed for new data structure
