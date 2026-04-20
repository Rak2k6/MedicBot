import cv2
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

def preprocess_image_for_ocr(pil_image: Image.Image) -> Image.Image:
    """
    Stage-2 Image Preprocessing:
    1. Grayscale conversion
    2. Shadow removal (crucial for phone scans)
    3. Noise reduction
    4. Adaptive thresholding
    5. Deskewing
    """
    try:
        # Convert PIL to cv2
        img = np.array(pil_image)
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            
        # 1. Shadow Removal / Illumination Correction
        # Dilate to get background, then median blur
        dilated_img = cv2.dilate(img, np.ones((7,7), np.uint8))
        bg_img = cv2.medianBlur(dilated_img, 21)
        
        # Calculate difference and normalize
        diff_img = 255 - cv2.absdiff(img, bg_img)
        norm_img = cv2.normalize(diff_img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
        
        # 2. Noise Reduction
        # Gaussian blur to remove high freq noise
        blur_img = cv2.GaussianBlur(norm_img, (3, 3), 0)
        
        # 3. Adaptive Thresholding
        # Helps with varying lighting conditions across the page
        thresh_img = cv2.adaptiveThreshold(
            blur_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # 4. Deskewing (simple projection based or minAreaRect)
        coords = np.column_stack(np.where(thresh_img > 0))
        angle = cv2.minAreaRect(coords)[-1]
        
        # Adjust angle
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        # Rotate if angle is significant (> 0.5 degrees)
        if abs(angle) > 0.5:
            (h, w) = thresh_img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            thresh_img = cv2.warpAffine(thresh_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
        return Image.fromarray(thresh_img)
        
    except Exception as e:
        logger.error(f"Image preprocessing failed: {e}")
        # Return original as fallback
        return pil_image
