import os
from PIL import Image
from flask import current_app

try:
    import pytesseract
except ImportError:
    pytesseract = None

def extract_text(filepath):
    """Attempts Tesseract OCR text extraction on target screenshot image.
    
    If successful, returns: (extracted_text, width, height, status='COMPLETE')
    If Tesseract-OCR is missing, returns: ('', width, height, status='METADATA_ONLY')
    """
    width = 0
    height = 0
    status = "METADATA_ONLY"
    extracted_text = ""

    # Ensure Pillow loaded safely to extract dimensions
    try:
        if os.path.exists(filepath):
            with Image.open(filepath) as img:
                width, height = img.size
    except Exception as e:
        current_app.logger.warning(f"AI Memory: Could not load image metadata for {filepath}: {e}")

    # Verify pytesseract exists
    if not pytesseract:
        current_app.logger.info(f"AI Memory: pytesseract library not installed. Falling back to metadata-only index: {filepath}")
        return extracted_text, width, height, status

    try:
        # Dry-run test of Tesseract binary presence
        # image_to_string will raise a TesseractNotFoundError if binary is not on host system PATH
        extracted_text = pytesseract.image_to_string(filepath, timeout=10.0)
        status = "COMPLETE"
        current_app.logger.info(f"AI Memory: OCR successful for screenshot: {os.path.basename(filepath)}")
    except Exception as ex:
        # Capture TesseractNotFoundError or any binary execution crash
        current_app.logger.warning(
            f"AI Memory: Tesseract OCR execution failed or binary not found. "
            f"Indexing file via metadata-only fallback. Reason: {ex}"
        )
        extracted_text = ""
        status = "METADATA_ONLY"

    return extracted_text, width, height, status
