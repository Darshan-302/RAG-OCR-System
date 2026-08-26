from abc import ABC, abstractmethod
import numpy as np


class EmbeddingsBase(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Convert text to embedding vector."""
        pass

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Convert multiple texts to embedding vectors."""
        pass

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Return the dimension of embedding vectors."""
        pass
