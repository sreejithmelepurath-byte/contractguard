"""PDF text extraction with an OCR fallback for scanned pages.

Text-based pages are read directly with PyMuPDF. Pages that yield almost no
text (scans, photos, rotated faxes) are rasterized and passed to Tesseract.
All of this is blocking, CPU-bound work, so callers run it in a thread.
"""
from dataclasses import dataclass

import fitz  # PyMuPDF
import pytesseract
from PIL import Image


@dataclass
class ExtractedText:
    text: str
    pages: int
    ocr_pages: int


class ExtractionError(ValueError):
    pass


def _ocr_page(page: "fitz.Page", dpi: int) -> str:
    pix = page.get_pixmap(dpi=dpi)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    # --psm 1: automatic page segmentation with orientation detection,
    # so rotated scans are still readable.
    return pytesseract.image_to_string(image, config="--psm 1")


def extract_text(pdf_bytes: bytes, dpi: int = 200, min_chars_per_page: int = 50) -> ExtractedText:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises several exception types
        raise ExtractionError("File is not a readable PDF.") from exc

    if doc.is_encrypted:
        raise ExtractionError("Password-protected PDFs are not supported.")

    parts: list[str] = []
    ocr_pages = 0
    with doc:
        for page in doc:
            text = page.get_text("text").strip()
            if len(text) < min_chars_per_page:
                text = _ocr_page(page, dpi).strip()
                ocr_pages += 1
            parts.append(text)
        page_count = doc.page_count

    full_text = "\n\n".join(p for p in parts if p)
    if not full_text.strip():
        raise ExtractionError("No readable text found in the PDF.")
    return ExtractedText(text=full_text, pages=page_count, ocr_pages=ocr_pages)
