import json
import logging
import os
import pickle
from typing import Optional

import numpy as np

from .base import VectorStoreBase

logger = logging.getLogger(__name__)


class FaissVectorStore(VectorStoreBase):
    def __init__(self, config: dict, embeddings):
        super().__init__(config, embeddings)
        self.config = config.get("faiss", {})
        self.index_path = self.config.get("index_path", "./data/faiss_index")
        self.dimension = self.config.get("dimension", embeddings.embedding_dimension)

        try:
            import faiss

            self.faiss = faiss
        except ImportError:
            logger.error("faiss not installed. Install with: pip install faiss-cpu or faiss-gpu")
            raise

        os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
        self.index = None
        self.id_map = {}
        self.documents = {}
        self._load_or_create_index()

    def _load_or_create_index(self):
        """Load existing index or create a new one."""
        index_file = f"{self.index_path}.idx"
        map_file = f"{self.index_path}.map"

        if os.path.exists(index_file) and os.path.exists(map_file):
            try:
                self.index = self.faiss.read_index(index_file)
                with open(map_file, "rb") as f:
                    self.id_map = pickle.load(f)
                logger.info(f"Loaded existing FAISS index from {index_file}")
            except Exception as e:
                logger.warning(f"Failed to load index: {e}, creating new one")
                self._create_new_index()
        else:
            self._create_new_index()

    def _create_new_index(self):
        """Create a new FAISS index."""
        self.index = self.faiss.IndexFlatL2(self.dimension)
        self.id_map = {}
        logger.info(f"Created new FAISS index with dimension {self.dimension}")

    def _save_index(self):
        """Save index to disk."""
        os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
        index_file = f"{self.index_path}.idx"
        map_file = f"{self.index_path}.map"

        self.faiss.write_index(self.index, index_file)
        with open(map_file, "wb") as f:
            pickle.dump(self.id_map, f)
        logger.info(f"Saved FAISS index to {index_file}")

    def add_documents(self, documents: list[dict]) -> None:
        """Add documents to FAISS."""
        try:
            embeddings = []
            ids = []

            for doc in documents:
                doc_id = doc["id"]
                text = doc["text"]
                embedding = self.embeddings.embed_text(text)

                embeddings.append(embedding)
                ids.append(doc_id)
                self.documents[doc_id] = doc

            embeddings_array = np.array(embeddings, dtype=np.float32)
            self.index.add(embeddings_array)

            for i, doc_id in enumerate(ids):
                self.id_map[self.index.ntotal - len(ids) + i] = doc_id

            self._save_index()
            logger.info(f"Added {len(documents)} documents to FAISS")
        except Exception as e:
            logger.error(f"Failed to add documents to FAISS: {e}")
            raise

    def search(self, query: str, k: int = 5) -> list[dict]:
        """Search for similar documents in FAISS."""
        try:
            query_embedding = self.embeddings.embed_text(query)
            query_embedding = np.array([query_embedding], dtype=np.float32)

            k = min(k, self.index.ntotal)
            distances, indices = self.index.search(query_embedding, k)

            documents = []
            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx in self.id_map:
                    doc_id = self.id_map[idx]
                    if doc_id in self.documents:
                        documents.append({
                            "id": doc_id,
                            "text": self.documents[doc_id]["text"],
                            "distance": float(distances[0][i]),
                            "metadata": self.documents[doc_id].get("metadata", {}),
                        })

            return documents
        except Exception as e:
            logger.error(f"Failed to search in FAISS: {e}")
            return []

    def delete(self, doc_id: str) -> None:
        """Delete document from FAISS."""
        logger.warning("FAISS does not support document deletion. Use clear() and re-add documents.")

    def clear(self) -> None:
        """Clear all documents from FAISS."""
        try:
            self._create_new_index()
            self.documents = {}
            self._save_index()
            logger.info("Cleared all documents from FAISS")
        except Exception as e:
            logger.error(f"Failed to clear FAISS: {e}")
            raise

    def get_document(self, doc_id: str) -> Optional[dict]:
        """Get document by ID."""
        return self.documents.get(doc_id)

    def list_documents(self) -> list[str]:
        """List all document IDs."""
        return list(self.documents.keys())
