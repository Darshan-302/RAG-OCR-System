import logging
import numpy as np

from .base import EmbeddingsBase

logger = logging.getLogger(__name__)


class TransformersEmbeddings(EmbeddingsBase):
    def __init__(self, config: dict):
        super().__init__(config)
        self.config = config.get("transformers", {})
        self.model_name = self.config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")
        self.device = self.config.get("device", "cuda")

        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"Loaded transformer model: {self.model_name} on {self.device}")
        except ImportError:
            logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
            raise

    def embed_text(self, text: str) -> np.ndarray:
        """Convert text to embedding vector."""
        embedding = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return embedding.astype(np.float32)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Convert multiple texts to embedding vectors."""
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
        return embeddings.astype(np.float32)

    @property
    def embedding_dimension(self) -> int:
        """Return the dimension of embedding vectors."""
        return self.model.get_sentence_embedding_dimension()
