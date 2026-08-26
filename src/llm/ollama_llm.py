import logging
from typing import Optional

import requests

from .base import LLMBase

logger = logging.getLogger(__name__)


class OllamaLLM(LLMBase):
    def __init__(self, config: dict):
        super().__init__(config)
        self.config = config.get("ollama", {})
        self.model = self.config.get("model", "qwen:3.8b")
        self.base_url = self.config.get("base_url", "http://localhost:11434")
        self.temperature = self.config.get("temperature", 0.7)
        self.top_p = self.config.get("top_p", 0.9)
        self.max_tokens = self.config.get("max_tokens", 2048)

    def _build_prompt(self, prompt: str, context: Optional[str] = None) -> str:
        """Build the full prompt with context."""
        if context:
            return f"Context:\n{context}\n\nQuestion:\n{prompt}"
        return prompt

    def generate(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate response from Ollama."""
        full_prompt = self._build_prompt(prompt, context)

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "num_predict": self.max_tokens,
                    "stream": False,
                },
                timeout=300,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            logger.error(f"Failed to generate response from Ollama: {e}")
            raise

    def generate_stream(self, prompt: str, context: Optional[str] = None):
        """Generate response from Ollama with streaming."""
        full_prompt = self._build_prompt(prompt, context)

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "num_predict": self.max_tokens,
                    "stream": True,
                },
                timeout=300,
                stream=True,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    import json

                    chunk = json.loads(line)
                    yield chunk.get("response", "")
        except Exception as e:
            logger.error(f"Failed to stream response from Ollama: {e}")
            raise
