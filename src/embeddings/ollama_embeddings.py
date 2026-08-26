import logging
import numpy as np
import requests

from .base import EmbeddingsBase

logger = logging.getLogger(__name__)


class OllamaEmbeddings(EmbeddingsBase):
    def __init__(self, config: dict):
        super().__init__(config)
        self.config = config.get("ollama", {})
        self.model = self.config.get("model", "nomic-embed-text")
        self.base_url = self.config.get("base_url", "http://localhost:11434")
        self._dimension = None

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a single text."""
        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text,
                },
                timeout=30,
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to get embedding from Ollama: {e}")
            raise

    def embed_text(self, text: str) -> np.ndarray:
        """Convert text to embedding vector."""
        return self._get_embedding(text)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Convert multiple texts to embedding vectors."""
        embeddings = []
        for text in texts:
            try:
                embedding = self._get_embedding(text)
                embeddings.append(embedding)
            except Exception as e:
                logger.warning(f"Failed to embed text: {e}")
                embeddings.append(np.zeros(self.embedding_dimension, dtype=np.float32))

        return np.array(embeddings, dtype=np.float32)

    @property
    def embedding_dimension(self) -> int:
        """Return the dimension of embedding vectors."""
        if self._dimension is None:
            test_embedding = self.embed_text("test")
            self._dimension = len(test_embedding)
            logger.info(f"Embedding dimension: {self._dimension}")
        return self._dimension
