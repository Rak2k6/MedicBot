import time
import os
import logging
from app.processing.easyocr_engine import EasyOCREngine
from PIL import Image

# Setup simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OCR-Benchmark")

def benchmark_ocr(image_path: str):
    if not os.path.exists(image_path):
        logger.error(f"File not found: {image_path}")
        return

    logger.info(f"Starting benchmark on {image_path}...")
    
    # Initialize Engine
    start_init = time.time()
    engine = EasyOCREngine(['en'])
    # Force load model
    engine.get_reader()
    init_time = time.time() - start_init
    logger.info(f"Engine Initialization (Model Load): {init_time:.2f}s")
    
    # Run Extraction
    start_ocr = time.time()
    text, structured = engine.extract_text(image_path)
    ocr_time = time.time() - start_ocr
    
    logger.info(f"OCR Execution Time: {ocr_time:.2f}s")
    
    # Analysis
    if structured:
        avg_conf = sum(item['confidence'] for item in structured) / len(structured)
        logger.info(f"Average Confidence: {avg_conf:.2f}")
        logger.info(f"Text Blocks Found: {len(structured)}")
    else:
        logger.warning("No text found!")
        
    print("\n--- Extracted Text Preview (First 500 chars) ---")
    print(text[:500])
    print("------------------------------------------------\n")

if __name__ == "__main__":
    # You can change this path to a sample image
    # For now, we'll try to find a sample in the repo if it exists, or just print usage.
    # Looking at file list, we don't have a sample image easily accessible in root 
    # except maybe extracted PDF artifacts, but those are JSONs.
    # We will let the user provide path or try a dummy call if they have one.
    
    import sys
    if len(sys.argv) > 1:
        benchmark_ocr(sys.argv[1])
    else:
        print("Usage: python verify_ocr_accuracy.py <path_to_image>")
        print("Please provide an image path to test.")
