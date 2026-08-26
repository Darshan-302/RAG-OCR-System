from abc import ABC, abstractmethod
from typing import Optional


class LLMBase(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def generate(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate response from LLM."""
        pass

    @abstractmethod
    def generate_stream(self, prompt: str, context: Optional[str] = None):
        """Generate response from LLM with streaming."""
        pass
