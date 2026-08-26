import logging
import os
import tempfile
import time
from typing import Optional

from .base import OCRBase

logger = logging.getLogger(__name__)


class TesseractOCR(OCRBase):
    def __init__(self, config: dict):
        super().__init__(config)
        self.config = config.get("tesseract", {})
        self.lang = self.config.get("lang", "eng")

        try:
            import pytesseract
            self.pytesseract = pytesseract
        except ImportError:
            logger.error("pytesseract not installed. Install with: pip install pytesseract")
            raise

    def extract_text(self, image_path: str) -> str:
        """Extract text from image using Tesseract OCR."""
        try:
            from PIL import Image

            img = Image.open(image_path)
            text = self.pytesseract.image_to_string(img, lang=self.lang)
            logger.info(f"Extracted text from {os.path.basename(image_path)}")
            return text
        except Exception as e:
            logger.error(f"Failed to extract text: {e}")
            return ""

    def extract_text_with_metadata(self, image_path: str) -> dict:
        """Extract text with metadata including confidence scores."""
        try:
            from PIL import Image

            img = Image.open(image_path)
            text = self.pytesseract.image_to_string(img, lang=self.lang)
            data = self.pytesseract.image_to_data(img, lang=self.lang)

            return {
                "text": text,
                "image_path": image_path,
                "ocr_method": "tesseract",
                "language": self.lang,
                "metadata": data,
                "timestamp": time.time(),
            }
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            return {"text": "", "error": str(e)}

    def process_pdf(self, pdf_path: str, output_dir: Optional[str] = None) -> dict:
        """Process PDF and extract text from each page."""
        try:
            import fitz
            from PIL import Image
        except ImportError:
            logger.error("PyMuPDF or PIL not installed")
            return {"error": "Required dependencies not installed"}

        doc = fitz.open(pdf_path)
        results = {"pages": [], "total_text": ""}
        tmp_dir = tempfile.mkdtemp(prefix="pdf_ocr_")

        dpi = 300
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        for i, page in enumerate(doc):
            try:
                pix = page.get_pixmap(matrix=mat)
                img_path = os.path.join(tmp_dir, f"page_{i + 1:04d}.png")
                pix.save(img_path)

                img = Image.open(img_path)
                page_text = self.pytesseract.image_to_string(img, lang=self.lang)

                results["pages"].append({
                    "page_num": i + 1,
                    "text": page_text,
                })
                results["total_text"] += f"\n--- Page {i + 1} ---\n{page_text}"

                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{i + 1:04d}.txt")
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(page_text)
                    logger.info(f"Saved page {i + 1} to {output_file}")

            except Exception as e:
                logger.error(f"Error processing page {i + 1}: {e}")
                results["pages"].append({"page_num": i + 1, "error": str(e)})

        doc.close()
        return results
