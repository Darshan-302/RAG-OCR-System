from abc import ABC, abstractmethod
from typing import Optional


class OCRBase(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def extract_text(self, image_path: str) -> str:
        """Extract text from image."""
        pass

    @abstractmethod
    def extract_text_with_metadata(self, image_path: str) -> dict:
        """Extract text with metadata (bounding boxes, confidence scores, etc.)."""
        pass

    @abstractmethod
    def process_pdf(self, pdf_path: str, output_dir: Optional[str] = None) -> dict:
        """Process PDF file and extract text from all pages."""
        pass
