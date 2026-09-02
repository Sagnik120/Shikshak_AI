"""OCR fallback handler for scanned or image-only documents.

Uses pytesseract and pdf2image when available, with graceful degradation.
"""

from __future__ import annotations

import io
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def extract_text_from_image_bytes(image_bytes: bytes) -> Tuple[str, float]:
    """Extract text from raw image bytes and estimate OCR confidence.

    Returns:
        Tuple of (extracted_text, avg_confidence_0_to_100)
    """
    try:
        from PIL import Image
        import pytesseract

        image = Image.open(io.BytesIO(image_bytes))
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        confidences = [int(conf) for conf in data.get("conf", []) if str(conf).isdigit() and int(conf) >= 0]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        
        text = pytesseract.image_to_string(image)
        return text.strip(), avg_conf
    except ImportError:
        logger.warning("pytesseract or PIL is not installed. OCR extraction unavailable.")
        return "", 0.0
    except Exception as e:
        logger.warning(f"OCR extraction failed: {e}")
        return "", 0.0


def extract_text_from_pdf_page_ocr(pdf_bytes: bytes, page_number: int) -> Tuple[str, float]:
    """Render a specific PDF page to image and perform OCR.

    Args:
        pdf_bytes: Raw bytes of the PDF file.
        page_number: 1-indexed page number.

    Returns:
        Tuple of (extracted_text, avg_confidence)
    """
    try:
        from pdf2image import convert_from_bytes
        
        images = convert_from_bytes(
            pdf_bytes,
            first_page=page_number,
            last_page=page_number,
            dpi=200
        )
        if not images:
            return "", 0.0
            
        from PIL import Image
        import pytesseract
        
        img = images[0]
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        confidences = [int(conf) for conf in data.get("conf", []) if str(conf).isdigit() and int(conf) >= 0]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        
        text = pytesseract.image_to_string(img)
        return text.strip(), avg_conf
    except ImportError:
        logger.warning("pdf2image or pytesseract not available for PDF page OCR.")
        return "", 0.0
    except Exception as e:
        logger.warning(f"PDF OCR failed for page {page_number}: {e}")
        return "", 0.0
