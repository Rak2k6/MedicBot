import pdfplumber
import json
import logging
import re
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import shutil
import io
import os
import google.genai as genai

logger = logging.getLogger(__name__)

def find_tesseract_binary():
    """Finds Tesseract binary on the system (Windows/Linux)."""
    # 1. Check if in PATH
    if shutil.which("tesseract"):
        return "tesseract"
    
    # 2. Check common Windows paths
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
            
    return None

def is_poor_quality_text(text: str) -> bool:
    """Determines if the extracted text is likely garbage or too sparse."""
    if not text or len(text.strip()) < 50:
        return True
    
    # Calculate alphanumeric ratio
    clean_text = re.sub(r'\s+', '', text)
    if not clean_text:
        return True
        
    alphanumeric = sum(c.isalnum() for c in clean_text)
    ratio = alphanumeric / len(clean_text)
    
    # If less than 70% alphanumeric, it might be garbage from a scan
    if ratio < 0.7:
        return True
        
    return False

def preprocess_image_for_ocr(pil_image):
    """Enhances image for better OCR results."""
    # Convert to grayscale
    gray_img = pil_image.convert('L')
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(gray_img)
    contrast_img = enhancer.enhance(2.0)
    
    return contrast_img

def extract_pdf_text(file_path: str) -> dict:
    """
    Advanced PDF extraction for lab reports.
    Extracts text, tables, uses OCR if needed, advanced parsing, and AI as last resort.
    Returns a dict with extracted data or None if extraction fails.
    """
    try:
        # Setup Tesseract
        tesseract_cmd = find_tesseract_binary()
        tesseract_available = False
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            tesseract_available = True
        else:
             # Check if it's already in path or configured
            try:
                pytesseract.get_tesseract_version()
                tesseract_available = True
            except:
                logger.warning("Tesseract not found. OCR specific features will be disabled.")

        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            extracted_text = ""
            tables = []
            ocr_text = ""
            
            # Extract text and tables from each page
            for page_num, page in enumerate(pdf.pages):
                # 1. Try standard text extraction
                raw_text = page.extract_text()
                
                # 2. Check quality
                if raw_text and not is_poor_quality_text(raw_text):
                    extracted_text += raw_text + "\n"
                else:
                    # Text is poor/missing. Try OCR if available.
                    if tesseract_available:
                        logger.info(f"Poor text quality on page {page_num+1}, attempting OCR...")
                        try:
                            # 3. Image conversion & preprocessing
                            # resolution=300 is good standard
                            original_image = page.to_image(resolution=300).original
                            processed_image = preprocess_image_for_ocr(original_image)
                            
                            # 4. OCR
                            page_ocr_text = pytesseract.image_to_string(processed_image)
                            ocr_text += page_ocr_text + "\n"
                            
                            # Use OCR text as primary if raw was garbage
                            extracted_text += page_ocr_text + "\n"
                        except Exception as e:
                            logger.warning(f"OCR failed on page {page_num+1}: {e}")
                            # Fallback to whatever raw text we had
                            extracted_text += (raw_text or "") + "\n"
                    else:
                        extracted_text += (raw_text or "") + "\n"

                # Extract tables
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)

            # Combine text sources - we've already built extracted_text to include OCR results where appropriate
            full_text = extracted_text
            
            # Advanced parsing for lab tests
            lab_tests = parse_lab_tests(full_text, tables)

            # Extract metadata
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            metadata = {
                "total_pages": total_pages,
                "file_size_bytes": file_size,
                "tables_found": len(tables),
                "ocr_used": bool(ocr_text.strip()),
                "tests_found": len(lab_tests)
            }

            result = {
                "extracted_text": extracted_text,
                "ocr_text": ocr_text,
                "tables": tables,
                "lab_tests": lab_tests,
                "metadata": metadata
            }

            # If no lab tests found, try AI as last resort
            if not lab_tests:
                logger.info("No lab tests found with standard methods, attempting AI extraction")
                ai_result = extract_with_ai(full_text, tables)
                if ai_result:
                    result["ai_extracted_tests"] = ai_result
                    result["metadata"]["ai_used"] = True
                else:
                    result["metadata"]["ai_used"] = False

            return result

    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return None

def parse_lab_tests(text: str, tables: list) -> dict:
    """
    Advanced parsing of lab tests from text and tables.
    """
    lab_tests = {}

    # Regex patterns for common lab report formats
    patterns = [
        r'(\w+(?:\s+\w+)*?)\s*:\s*([\d.]+)\s*(\w+)',  # Test: value unit
        r'(\w+(?:\s+\w+)*?)\s+([\d.]+)\s+(\w+)',  # Test value unit
        r'(\w+(?:\s+\w+)*?)\s+([\d.]+)\s+(\w+)\s+\(([\d.-]+)\s*-\s*([\d.-]+)\)',  # Test value unit (range)
    ]

    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                test_name = match.group(1).strip()
                value = match.group(2)
                unit = match.group(3)
                reference_range = match.group(4) + "-" + match.group(5) if len(match.groups()) > 3 else None

                try:
                    float(value)
                    lab_tests[test_name] = {
                        "value": value,
                        "unit": unit,
                        "reference_range": reference_range,
                        "raw_line": line
                    }
                except ValueError:
                    continue
                break  # Use first matching pattern

    # Parse tables for additional data
    for table in tables:
        for row in table:
            if len(row) >= 3:
                test_name = str(row[0]).strip() if row[0] else ""
                value = str(row[1]).strip() if row[1] else ""
                unit = str(row[2]).strip() if row[2] else ""

                if test_name and value and unit:
                    try:
                        float(value)
                        lab_tests[test_name] = {
                            "value": value,
                            "unit": unit,
                            "reference_range": None,
                            "raw_line": str(row)
                        }
                    except ValueError:
                        continue

    return lab_tests

def extract_with_ai(text: str, tables: list) -> dict:
    """
    Use Google Gemini AI as last resort for extraction.
    """
    try:
        # Configure Gemini (assuming API key is set in env)
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set, skipping AI extraction")
            return None

        client = genai.Client(api_key=api_key)
        model = "gemini-2.0-flash-exp"

        prompt = f"""
        Extract lab test results from the following medical report text and tables.
        Return a JSON object with test names as keys and objects containing 'value', 'unit', 'reference_range' as values.
        If no tests found, return empty object.

        Text:
        {text[:4000]}  # Limit text length

        Tables:
        {json.dumps(tables[:5])}  # Limit tables
        """

        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        ai_text = response.text.strip()

        # Try to parse JSON from AI response
        try:
            ai_tests = json.loads(ai_text)
            return ai_tests if isinstance(ai_tests, dict) else None
        except json.JSONDecodeError:
            logger.warning("AI response not valid JSON")
            return None

    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        return None
