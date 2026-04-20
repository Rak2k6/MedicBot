import easyocr
import numpy as np
import logging
from typing import List, Dict, Tuple, Any

logger = logging.getLogger(__name__)

class EasyOCREngine:
    """
    Wrapper for EasyOCR to handle initialization, execution, and layout reconstruction.
    """
    _reader = None

    @classmethod
    def get_reader(cls, languages: List[str] = ['en'], gpu: bool = False):
        """
        Lazy initialization of the EasyOCR reader to avoid startup overhead until needed.
        """
        if cls._reader is None:
            logger.info(f"Initializing EasyOCR with languages={languages}, gpu={gpu}...")
            # verbose=False to reduce console spam
            cls._reader = easyocr.Reader(languages, gpu=gpu, verbose=False)
        return cls._reader

    def __init__(self, languages: List[str] = ['en'], gpu: bool = False):
        self.languages = languages
        self.gpu = gpu

    def extract_text(self, image: Any, confidence_threshold: float = 0.3) -> Tuple[str, List[Dict]]:
        """
        Extracts text from an image using EasyOCR.
        
        Args:
            image: File path, URL, or numpy array (Opencv/PIL).
            confidence_threshold: Minimum confidence to include a block.
            
        Returns:
            Tuple of (combined_text_string, raw_structured_data)
        """
        reader = self.get_reader(self.languages, self.gpu)
        
        # Convert PIL Image to numpy array if necessary
        try:
            from PIL import Image
            if isinstance(image, Image.Image):
                image = np.array(image)
        except ImportError:
            pass
            
        # detail=1 returns [ [ [x1,y1],[x2,y2],[x3,y3],[x4,y4] ], "text", confidence ]
        try:
            results = reader.readtext(image, detail=1, paragraph=False)
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}")
            return "", []

        # Filter by confidence
        filtered_results = [res for res in results if res[2] >= confidence_threshold]
        
        if not filtered_results:
            return "", []

        # Sort structure to reconstruct reading order (Top-Down, Left-Right)
        sorted_results = self._sort_reading_order(filtered_results)
        
        # Combine text
        # distinct lines should be separated by \n, same line blocks by space.
        # The sorting sorts into lines, so we can reconstruct.
        combined_text = self._reconstruct_text(sorted_results)
        
        # Format output for potential downstream usage
        structured_output = []
        for bbox, text, conf in sorted_results:
             structured_output.append({
                 "box": [list(map(int, pt)) for pt in bbox], # Convert numpy ints/floats to standard
                 "text": text,
                 "confidence": float(conf)
             })

        return combined_text, structured_output

    def _sort_reading_order(self, results: List[Tuple], y_threshold: int = 10) -> List[Tuple]:
        """
        Sorts bounding boxes to mimic natural reading order.
        1. Sort all by Top-Y (y_min).
        2. Cluster into lines based on y_threshold.
        3. Sort within lines by Left-X (x_min).
        """
        # res format: [bbox, text, conf]
        # bbox is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]] usually
        
        # Helper to get y_min, x_min
        def get_coords(res):
            box = res[0]
            return min(p[0] for p in box), min(p[1] for p in box) # x_min, y_min

        # Sort primarily by accurate Y first to get roughly top-down
        # This is just a preliminary sort
        results.sort(key=lambda r: get_coords(r)[1])

        lines = []
        current_line = []
        
        if not results:
            return []

        # Initialize first line
        current_line_y = get_coords(results[0])[1]
        current_line.append(results[0])
        
        for i in range(1, len(results)):
            box = results[i]
            x, y = get_coords(box)
            
            # Check if this box belongs to the current line (similar Y)
            # We use the center Y or simply the Top Y. Top Y is usually sufficient for printed text.
            if abs(y - current_line_y) < y_threshold:
                current_line.append(box)
            else:
                # Finish current line
                # Sort current line by X
                current_line.sort(key=lambda r: get_coords(r)[0])
                lines.extend(current_line)
                
                # Start new line
                current_line = [box]
                current_line_y = y
        
        # Append last line
        if current_line:
            current_line.sort(key=lambda r: get_coords(r)[0])
            lines.extend(current_line)
            
        return lines

    def _reconstruct_text(self, sorted_results: List[Tuple]) -> str:
        """
        Joins sorted results into a single string.
        Logic: 
        - If boxes are on the same "line" (handled by sorting logic clustering), join with space.
        - If new line, join with newline.
        Since we flattened the list in _sort_reading_order, we need to re-detect line breaks 
        or simply modify _sort_reading_order to return list of lists.
        
        Refactoring _sort slightly would be cleaner, but let's stick to the flat list 
        and use Y-diff to detect newlines again for string generation, 
        OR just accept that _sort_reading_order ensures order, 
        but implementation details of strict row alignment might need `\n`.
        """
        
        if not sorted_results:
            return ""

        text_lines = []
        
        # We need to re-group to insert newlines correctly
        # Re-using the logic from sort, essentially
        
        current_line_texts = []
        last_y = min(p[1] for p in sorted_results[0][0])
        y_threshold = 10 # Same threshold
        
        for res in sorted_results:
            box, text, _ = res
            y = min(p[1] for p in box)
            
            if abs(y - last_y) >= y_threshold and current_line_texts:
                 # New line detected
                 text_lines.append(" ".join(current_line_texts))
                 current_line_texts = []
                 last_y = y # Update reference Y for the new line
            
            current_line_texts.append(text)
            
        if current_line_texts:
            text_lines.append(" ".join(current_line_texts))
            
        return "\n".join(text_lines)
