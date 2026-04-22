import os
import logging
import subprocess
import shutil
import re
import pdfplumber

logger = logging.getLogger(__name__)

def is_ocrmypdf_available() -> bool:
    """Checks if ocrmypdf is installed."""
    try:
        import ocrmypdf
        return True
    except ImportError:
        return False


def has_text_layer(pdf_path: str) -> bool:
    """
    Checks if a PDF has a selectable text layer.
    Returns True if valid text is found, False otherwise (indicating a scanned document).
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Check the first few pages to see if any words can be extracted
            for page in pdf.pages[:3]:
                words = page.extract_words()
                if words and len(words) > 10:
                    return True
        return False
    except Exception as e:
        logger.error(f"Error checking text layer for {pdf_path}: {e}")
        return False


def run_ocrmypdf(input_pdf: str, output_pdf: str) -> bool:
    """
    Runs ocrmypdf on the input_pdf to create a searchable output_pdf.
    Uses default settings with force-ocr to handle tricky scans.
    Returns True if successful, False otherwise.
    """
    if not is_ocrmypdf_available():
        logger.warning("OCRmyPDF is not installed or not in PATH. Skipping OCRmyPDF preprocessing.")
        return False

    try:
        import ocrmypdf
        logger.info(f"Running OCRmyPDF on {input_pdf}...")
        # --force-ocr will rasterize all vector content and run OCR
        ocrmypdf.ocr(input_pdf, output_pdf, force_ocr=True)

        logger.info("OCRmyPDF completed successfully.")
        return True

    except Exception as e:
        logger.error(f"Exception while running OCRmyPDF: {e}")
        return False


def post_ocr_normalization(text: str) -> str:
    """
    Fix common OCR issues:
    - replace "," with "." in numeric context (e.g. 97,5 -> 97.5)
    - normalize units (mg/d| -> mg/dL)
    """
    if not text:
        return text
    
    # Replace comma in numeric context (e.g. 1,23 -> 1.23)
    # Caution to avoid changing thousands separators if not needed, 
    # but in most lab context, Europeans use comma for decimal, OCR messes up.
    text = re.sub(r'(\d),(\d)', r'\1.\2', text)

    # Normalize weird units
    text = text.replace("mg/d|", "mg/dL")
    text = text.replace("g/d|", "g/dL")
    text = text.replace("/u|", "/uL")
    text = text.replace("mI/L", "mL/L")

    return text
