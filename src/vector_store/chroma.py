import logging
import os
from typing import Optional

from .base import VectorStoreBase

logger = logging.getLogger(__name__)


class ChromaVectorStore(VectorStoreBase):
    def __init__(self, config: dict, embeddings):
        super().__init__(config, embeddings)
        self.config = config.get("chroma", {})
        self.persist_directory = self.config.get("persist_directory", "./data/chroma_db")
        self.collection_name = self.config.get("collection_name", "ocr_documents")

        try:
            import chromadb
            from chromadb.config import Settings

            os.makedirs(self.persist_directory, exist_ok=True)

            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"Initialized Chroma collection: {self.collection_name}")
        except ImportError:
            logger.error("chromadb not installed. Install with: pip install chromadb")
            raise

    def add_documents(self, documents: list[dict]) -> None:
        """Add documents to Chroma."""
        ids = []
        metadatas = []
        documents_text = []

        for doc in documents:
            ids.append(doc["id"])
            documents_text.append(doc["text"])
            metadatas.append(doc.get("metadata", {}))

        try:
            self.collection.upsert(
                ids=ids,
                documents=documents_text,
                metadatas=metadatas,
            )
            logger.info(f"Added {len(documents)} documents to Chroma")
        except Exception as e:
            logger.error(f"Failed to add documents to Chroma: {e}")
            raise

    def search(self, query: str, k: int = 5) -> list[dict]:
        """Search for similar documents in Chroma."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=k,
            )

            documents = []
            if results["ids"] and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    documents.append({
                        "id": doc_id,
                        "text": results["documents"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else 0,
                        "metadata": results["metadatas"][0][i] if "metadatas" in results else {},
                    })

            return documents
        except Exception as e:
            logger.error(f"Failed to search in Chroma: {e}")
            return []

    def delete(self, doc_id: str) -> None:
        """Delete document from Chroma."""
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise

    def clear(self) -> None:
        """Clear all documents from Chroma."""
        try:
            all_ids = self.list_documents()
            if all_ids:
                self.collection.delete(ids=all_ids)
            logger.info("Cleared all documents from Chroma")
        except Exception as e:
            logger.error(f"Failed to clear Chroma: {e}")
            raise

    def get_document(self, doc_id: str) -> Optional[dict]:
        """Get document by ID from Chroma."""
        try:
            result = self.collection.get(ids=[doc_id])
            if result["ids"]:
                return {
                    "id": result["ids"][0],
                    "text": result["documents"][0],
                    "metadata": result["metadatas"][0],
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None

    def list_documents(self) -> list[str]:
        """List all document IDs in Chroma."""
        try:
            result = self.collection.get()
            return result["ids"] if result["ids"] else []
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
