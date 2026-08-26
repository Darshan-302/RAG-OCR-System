from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class VectorStoreBase(ABC):
    def __init__(self, config: dict, embeddings):
        self.config = config
        self.embeddings = embeddings

    @abstractmethod
    def add_documents(self, documents: list[dict]) -> None:
        """Add documents to vector store.

        Each document should have:
        - id: unique identifier
        - text: document text
        - metadata: (optional) dict with metadata
        """
        pass

    @abstractmethod
    def search(self, query: str, k: int = 5) -> list[dict]:
        """Search for similar documents."""
        pass

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """Delete document by ID."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all documents from vector store."""
        pass

    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[dict]:
        """Get document by ID."""
        pass

    @abstractmethod
    def list_documents(self) -> list[str]:
        """List all document IDs."""
        pass
