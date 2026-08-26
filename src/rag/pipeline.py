import logging
from typing import Optional
import uuid

from ..ocr import OCRBase
from ..embeddings import EmbeddingsBase
from ..vector_store import VectorStoreBase
from ..llm import LLMBase

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self,
        ocr: OCRBase,
        embeddings: EmbeddingsBase,
        vector_store: VectorStoreBase,
        llm: LLMBase,
        config: dict,
    ):
        self.ocr = ocr
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.llm = llm
        self.config = config.get("rag", {})
        self.chunk_size = self.config.get("chunk_size", 512)
        self.chunk_overlap = self.config.get("chunk_overlap", 50)
        self.top_k = self.config.get("top_k_retrieval", 5)
        self.similarity_threshold = self.config.get("similarity_threshold", 0.5)

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        step = self.chunk_size - self.chunk_overlap

        for i in range(0, len(text), step):
            chunk = text[i : i + self.chunk_size]
            if len(chunk.strip()) > 0:
                chunks.append(chunk)

        return chunks

    def ingest_image(self, image_path: str, metadata: Optional[dict] = None) -> str:
        """Process image with OCR and ingest into RAG."""
        logger.info(f"Processing image: {image_path}")

        # Extract text from image
        extracted_data = self.ocr.extract_text_with_metadata(image_path)
        text = extracted_data["text"]

        if not text.strip():
            logger.warning(f"No text extracted from image: {image_path}")
            return ""

        # Chunk the text
        chunks = self._chunk_text(text)
        logger.info(f"Created {len(chunks)} chunks from image")

        # Create documents and add to vector store
        documents = []
        doc_id_base = str(uuid.uuid4())

        for i, chunk in enumerate(chunks):
            doc_id = f"{doc_id_base}_{i}"
            doc_metadata = {
                "source": image_path,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "ocr_method": extracted_data.get("ocr_method", "unknown"),
            }
            if metadata:
                doc_metadata.update(metadata)

            documents.append({
                "id": doc_id,
                "text": chunk,
                "metadata": doc_metadata,
            })

        self.vector_store.add_documents(documents)
        logger.info(f"Ingested {len(documents)} documents from image")

        return doc_id_base

    def ingest_pdf(self, pdf_path: str, metadata: Optional[dict] = None) -> str:
        """Process PDF with OCR and ingest into RAG."""
        logger.info(f"Processing PDF: {pdf_path}")

        # Extract text from PDF
        result = self.ocr.process_pdf(pdf_path)

        if "error" in result:
            logger.error(f"Error processing PDF: {result['error']}")
            return ""

        pages = result.get("pages", [])
        doc_id_base = str(uuid.uuid4())
        total_documents = 0

        for page_info in pages:
            if "error" in page_info:
                logger.warning(f"Error on page {page_info['page_num']}: {page_info['error']}")
                continue

            text = page_info.get("text", "")
            page_num = page_info.get("page_num", 0)

            if not text.strip():
                logger.warning(f"No text extracted from page {page_num}")
                continue

            # Chunk the text
            chunks = self._chunk_text(text)

            # Create documents and add to vector store
            documents = []
            for i, chunk in enumerate(chunks):
                doc_id = f"{doc_id_base}_page_{page_num}_chunk_{i}"
                doc_metadata = {
                    "source": pdf_path,
                    "page_num": page_num,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
                if metadata:
                    doc_metadata.update(metadata)

                documents.append({
                    "id": doc_id,
                    "text": chunk,
                    "metadata": doc_metadata,
                })

            self.vector_store.add_documents(documents)
            total_documents += len(documents)

        logger.info(f"Ingested {total_documents} documents from PDF")
        return doc_id_base

    def retrieve(self, query: str, k: Optional[int] = None) -> list[dict]:
        """Retrieve relevant documents for a query."""
        if k is None:
            k = self.top_k

        logger.info(f"Retrieving top {k} documents for query: {query}")
        results = self.vector_store.search(query, k=k)

        # Filter by similarity threshold if using distance-based search
        filtered_results = []
        for result in results:
            distance = result.get("distance", 0)
            # Convert L2 distance to similarity (lower distance = higher similarity)
            # For L2 distance, threshold filtering may not apply, so we include all
            filtered_results.append(result)

        logger.info(f"Retrieved {len(filtered_results)} documents")
        return filtered_results

    def query(self, question: str, use_stream: bool = False) -> str:
        """Execute full RAG pipeline: retrieve and generate."""
        logger.info(f"Processing query: {question}")

        # Retrieve relevant documents
        retrieved_docs = self.retrieve(question)

        if not retrieved_docs:
            logger.warning("No relevant documents found")
            context = "No relevant documents found in the knowledge base."
        else:
            # Build context from retrieved documents
            context_parts = []
            for i, doc in enumerate(retrieved_docs, 1):
                source = doc.get("metadata", {}).get("source", "Unknown")
                context_parts.append(f"[Document {i} from {source}]\n{doc['text']}")

            context = "\n\n".join(context_parts)

        # Generate response
        if use_stream:
            logger.info("Generating response (streaming)")
            return self.llm.generate_stream(question, context=context)
        else:
            logger.info("Generating response")
            return self.llm.generate(question, context=context)

    def clear_knowledge_base(self) -> None:
        """Clear all documents from vector store."""
        logger.warning("Clearing knowledge base")
        self.vector_store.clear()

    def list_documents(self) -> list[str]:
        """List all documents in vector store."""
        return self.vector_store.list_documents()

    def get_statistics(self) -> dict:
        """Get statistics about the knowledge base."""
        doc_ids = self.list_documents()
        return {
            "total_documents": len(doc_ids),
            "embedding_dimension": self.embeddings.embedding_dimension,
            "vector_store_type": type(self.vector_store).__name__,
            "llm_model": self.llm.model,
            "ocr_type": type(self.ocr).__name__,
        }
