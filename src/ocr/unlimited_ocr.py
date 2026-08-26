import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from typing import Optional

import requests

from .base import OCRBase

logger = logging.getLogger(__name__)


class UnlimitedOCR(OCRBase):
    def __init__(self, config: dict):
        super().__init__(config)
        self.config = config.get("unlimited_ocr", {})
        self.model_dir = self.config.get("model_dir", "baidu/Unlimited-OCR")
        self.image_mode = self.config.get("image_mode", "gundam")
        self.gpu = self.config.get("gpu", "0")
        self.server_url = "http://127.0.0.1:10000"
        self.server_process = None
        self.prompt = "document parsing."
        self.temperature = 0
        self.max_retries = 3

    def _start_server(self):
        """Start SGLang server if not already running."""
        if self._server_ready():
            logger.info(f"Reusing existing server at {self.server_url}")
            return

        logger.info(f"Starting SGLang server on GPU {self.gpu}...")
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = self.gpu

        cmd = [
            sys.executable,
            "-m",
            "sglang.launch_server",
            "--model",
            self.model_dir,
            "--served-model-name",
            "Unlimited-OCR",
            "--attention-backend",
            "fa3",
            "--page-size",
            "1",
            "--mem-fraction-static",
            "0.8",
            "--context-length",
            "32768",
            "--disable-overlap-schedule",
            "--skip-server-warmup",
            "--host",
            "0.0.0.0",
            "--port",
            "10000",
        ]

        os.makedirs("./logs", exist_ok=True)
        log_file = open("./logs/sglang_server.log", "w", encoding="utf-8")
        self.server_process = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT)
        logger.info(f"Server started with PID: {self.server_process.pid}")

        start = time.time()
        timeout = 300
        while time.time() - start < timeout:
            if self.server_process.poll() is not None:
                raise RuntimeError("SGLang server exited early. Check ./logs/sglang_server.log")
            if self._server_ready():
                logger.info(f"Server ready after {time.time() - start:.0f}s")
                return
            time.sleep(3)

        raise TimeoutError(f"SGLang server startup timed out after {timeout}s")

    def _server_ready(self) -> bool:
        try:
            resp = requests.get(f"{self.server_url}/health", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def _encode_image(self, image_path: str) -> dict:
        ext = os.path.splitext(image_path)[1].lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext.lstrip('.')}"
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}

    def _build_content(self, image_path: str) -> list[dict]:
        return [{"type": "text", "text": self.prompt}, self._encode_image(image_path)]

    def extract_text(self, image_path: str) -> str:
        """Extract text from image using Unlimited-OCR."""
        if not self._server_ready():
            self._start_server()

        payload = {
            "model": "Unlimited-OCR",
            "messages": [{"role": "user", "content": self._build_content(image_path)}],
            "temperature": self.temperature,
            "skip_special_tokens": False,
            "stream": False,
            "images_config": {"image_mode": self.image_mode},
        }

        for attempt in range(self.max_retries):
            try:
                resp = requests.post(
                    f"{self.server_url}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=300,
                )
                resp.raise_for_status()
                result = resp.json()
                text = result["choices"][0]["message"]["content"]
                logger.info(f"Extracted text from {os.path.basename(image_path)}")
                return text
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Retry {attempt + 1}/{self.max_retries}: {e}")
                    time.sleep(3 * (attempt + 1))
                else:
                    logger.error(f"Failed to extract text: {e}")
                    return ""

    def extract_text_with_metadata(self, image_path: str) -> dict:
        """Extract text with metadata."""
        text = self.extract_text(image_path)
        return {
            "text": text,
            "image_path": image_path,
            "ocr_method": "unlimited_ocr",
            "model": self.model_dir,
            "timestamp": time.time(),
        }

    def process_pdf(self, pdf_path: str, output_dir: Optional[str] = None) -> dict:
        """Process PDF and extract text from each page."""
        try:
            import fitz
        except ImportError:
            logger.error("PyMuPDF not installed. Install with: pip install PyMuPDF")
            return {"error": "PyMuPDF not installed"}

        doc = fitz.open(pdf_path)
        tmp_dir = tempfile.mkdtemp(prefix="pdf_ocr_")
        results = {"pages": [], "total_text": ""}

        dpi = 300
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        for i, page in enumerate(doc):
            try:
                out_path = os.path.join(tmp_dir, f"page_{i + 1:04d}.png")
                page.get_pixmap(matrix=mat).save(out_path)

                page_text = self.extract_text(out_path)
                results["pages"].append({
                    "page_num": i + 1,
                    "text": page_text,
                })
                results["total_text"] += f"\n--- Page {i + 1} ---\n{page_text}"

                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{i + 1:04d}.md")
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(page_text)
                    logger.info(f"Saved page {i + 1} to {output_file}")

            except Exception as e:
                logger.error(f"Error processing page {i + 1}: {e}")
                results["pages"].append({"page_num": i + 1, "error": str(e)})

        doc.close()
        return results

    def stop_server(self):
        """Stop the SGLang server."""
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait()
            logger.info("SGLang server stopped")
