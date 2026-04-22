import pdfplumber
import json
import logging
import re
# import pytesseract (Removed)
from PIL import Image, ImageOps, ImageEnhance
import shutil
import io
import os
from .image_processing import preprocess_image_for_ocr
from .easyocr_engine import EasyOCREngine
from .layout_parser import LayoutParser
from .ocr_utils import has_text_layer, run_ocrmypdf, post_ocr_normalization
from .document_classifier import classify_document
from .clinical_extractor import extract_clinical_data
from .radiology_extractor import extract_radiology_data
from typing import List, Dict, Any
import tempfile
from config.defaults import get_setting

logger = logging.getLogger(__name__)

def ocr_pdf_pages_as_images(file_path: str) -> str:
    """
    Explicitly converts each PDF page to an image and runs OCR,
    bypassing digital text checks.
    """
    all_text = []
    
    try:
        # Initialize OCR Engine
        engine = EasyOCREngine(['en'])
        
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                logger.info(f"Processing page {i+1} as image for OCR...")
                
                # Convert to high-res image
                original_img = page.to_image(resolution=300).original
                
                # Preprocess
                processed_img = preprocess_image_for_ocr(original_img)
                
                # Run OCR
                text, _ = engine.extract_text(processed_img)
                all_text.append(text)
                
        return "\n".join(all_text)

    except Exception as e:
        logger.error(f"Failed to OCR PDF as images: {e}")
        return ""


# Tesseract binary check removed


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

class LabReportExtractor:
    """
    Stage-2 OCR Pipeline for Lab Reports (Powered by EasyOCR).
    Handles image preprocessing, layout-aware OCR, validation, and normalization.
    """
    
    def __init__(self):
        # Initialize EasyOCR
        try:
            self.ocr_engine = EasyOCREngine(['en'])
            self.ocr_available = True
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            self.ocr_available = False
            
        self.layout_parser = LayoutParser()
        self.ocr_config = get_setting("ocr_config") or {}

    def _run_ocr_with_layout(self, image) -> List[Dict[str, Any]]:
        """Runs EasyOCR and returns tokens with layout info."""
        if not self.ocr_available:
            return []
        try:
            # EasyOCR returns (combined_text, structured_output)
            # structured_output is List[Dict] with "box", "text", "confidence"
            _, structured_output = self.ocr_engine.extract_text(image)
            return self.layout_parser.convert_to_unified_format(structured_output, "easyocr")
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return []

    def process_pdf(self, file_path: str) -> dict:
        """Main execution method (Refactored for Layout-Aware Parsing)."""
        all_tokens = []
        total_pages = 0
        ocr_used = False
        
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages):
                # 1. Try digital extraction first (words with coordinates)
                page_words = page.extract_words()
                
                # 2. Coverage Check: If text is sparse or missing, use OCR
                # We check raw text quality to decide if we need OCR
                raw_text = page.extract_text() or ""
                
                if (not page_words or is_poor_quality_text(raw_text)) and self.ocr_available:
                    logger.info(f"Page {page_num+1}: Poor text quality/Image, running Stage-2 OCR pipeline...")
                    
                    try:
                        # Image Preprocessing
                        original_img = page.to_image(resolution=300).original
                        processed_img = preprocess_image_for_ocr(original_img)
                        
                        # Layout-Aware OCR
                        ocr_tokens = self._run_ocr_with_layout(processed_img)
                        all_tokens.extend(ocr_tokens)
                        ocr_used = True
                    except Exception as e:
                        logger.error(f"Stage-2 Preprocessing/OCR failed on page {page_num+1}: {e}")
                else:
                    # Use digital words
                    page_tokens = self.layout_parser.convert_to_unified_format(page_words, "pdfplumber")
                    all_tokens.extend(page_tokens)

        # 3. Parse Document using Layout-Aware State Machine
        all_lab_tests = self.layout_parser.parse_document(all_tokens)

        # 4. Generate combined text for legacy support (optional but helpful)
        extracted_text = "\n".join([" ".join([t["text"] for t in row]) 
                                    for row in self.layout_parser.group_rows(all_tokens)])

        result = {
            "extracted_text": extracted_text,
            "lab_tests": all_lab_tests,
            "metadata": {
                "total_pages": total_pages,
                "file_size_bytes": os.path.getsize(file_path),
                "ocr_used": ocr_used,
                "tests_found": len(all_lab_tests),
                "stage_2_pipeline": True,
                "layout_aware_parsing": True,
                "parser_type": "state_machine",
                "report_type": "clinical_pathology"
            }
        }
        return result


def extract_pdf_text(file_path: str) -> dict:
    """
    Entry point for PDF extraction.
    Delegates to appropriate extractor based on document type.
    """
    try:
        # 1. Preprocessing: Check for text layer and ocrmypdf
        target_pdf_path = file_path
        cleanup_needed = False
        
        if not has_text_layer(file_path):
            logger.info("No text layer found. Attempting OCRmyPDF preprocessing...")
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(tmp_fd)
            if run_ocrmypdf(file_path, tmp_path):
                target_pdf_path = tmp_path
                cleanup_needed = True

        # Extract Raw Text for classification
        raw_text = ""
        with pdfplumber.open(target_pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"
                    
        # If still no text, fallback to extracting as images with easyocr
        if not raw_text.strip():
             raw_text = ocr_pdf_pages_as_images(target_pdf_path)

        # 2. Normalize text
        normalized_text = post_ocr_normalization(raw_text)
        
        # 3. Classification
        doc_type = classify_document(normalized_text)
        logger.info(f"Document classified as: {doc_type}")
        
        # 4. Routing logic
        unified_result = {
            "document_type": doc_type,
            "lab_tests": [],
            "vitals": {},
            "findings": {},
            "impression": [],
            "extracted_text": normalized_text
        }

        if doc_type == "lab":
            extractor = LabReportExtractor()
            lab_result = extractor.process_pdf(target_pdf_path)
            
            # Map legacy lab format back into the unified result
            extracted_tests = lab_result.get("lab_tests", {})
            test_list = []
            if isinstance(extracted_tests, dict):
                for k, v in extracted_tests.items():
                    test_list.append({
                        "test_name": k,
                        "value": v.get("value"),
                        "unit": v.get("unit"),
                        "reference_range": v.get("reference_range")
                    })
            elif isinstance(extracted_tests, list):
                test_list = extracted_tests
                
            unified_result["lab_tests"] = test_list
            unified_result["metadata"] = lab_result.get("metadata", {})
            unified_result["metadata"]["document_type"] = "lab"
            
        elif doc_type == "radiology":
            rad_data = extract_radiology_data(normalized_text)
            unified_result.update(rad_data)
            unified_result["metadata"] = {"document_type": "radiology"}
            
        elif doc_type == "clinical":
            clin_data = extract_clinical_data(normalized_text)
            unified_result.update(clin_data)
            unified_result["metadata"] = {"document_type": "clinical"}
            
        # Cleanup temp file
        if cleanup_needed and os.path.exists(target_pdf_path):
            os.remove(target_pdf_path)
            
        return unified_result

    except Exception as e:
        logger.error(f"Error in extract_pdf_text: {e}")
        return None
