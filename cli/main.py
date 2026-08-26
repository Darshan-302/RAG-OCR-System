#!/usr/bin/env python3

import argparse
import logging
import os
import sys
import yaml
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ocr import UnlimitedOCR, TesseractOCR
from src.embeddings import OllamaEmbeddings, TransformersEmbeddings
from src.vector_store import ChromaVectorStore, FaissVectorStore
from src.llm import OllamaLLM
from src.rag import RAGPipeline

# Setup logging
def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    level = getattr(logging, log_level.upper())
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(level=level, format=format_str, handlers=handlers)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def create_ocr(config: dict) -> any:
    """Create OCR instance based on config."""
    ocr_type = config["ocr"]["type"]
    if ocr_type == "unlimited_ocr":
        return UnlimitedOCR(config["ocr"])
    elif ocr_type == "tesseract":
        return TesseractOCR(config["ocr"])
    else:
        raise ValueError(f"Unknown OCR type: {ocr_type}")


def create_embeddings(config: dict) -> any:
    """Create embeddings instance based on config."""
    emb_type = config["embeddings"]["type"]
    if emb_type == "ollama":
        return OllamaEmbeddings(config["embeddings"])
    elif emb_type == "transformers":
        return TransformersEmbeddings(config["embeddings"])
    else:
        raise ValueError(f"Unknown embeddings type: {emb_type}")


def create_vector_store(config: dict, embeddings: any) -> any:
    """Create vector store instance based on config."""
    vs_type = config["vector_store"]["type"]
    if vs_type == "chroma":
        return ChromaVectorStore(config["vector_store"], embeddings)
    elif vs_type == "faiss":
        return FaissVectorStore(config["vector_store"], embeddings)
    else:
        raise ValueError(f"Unknown vector store type: {vs_type}")


def create_llm(config: dict) -> any:
    """Create LLM instance based on config."""
    llm_type = config["llm"]["type"]
    if llm_type == "ollama":
        return OllamaLLM(config["llm"])
    else:
        raise ValueError(f"Unknown LLM type: {llm_type}")


def create_pipeline(config_path: str) -> RAGPipeline:
    """Create RAG pipeline from config."""
    config = load_config(config_path)

    # Setup logging
    log_config = config.get("logging", {})
    setup_logging(log_config.get("level", "INFO"), log_config.get("file"))

    logger = logging.getLogger(__name__)
    logger.info(f"Loading config from {config_path}")

    # Create components
    ocr = create_ocr(config)
    embeddings = create_embeddings(config)
    vector_store = create_vector_store(config, embeddings)
    llm = create_llm(config)

    # Create pipeline
    pipeline = RAGPipeline(ocr, embeddings, vector_store, llm, config)
    logger.info("RAG pipeline initialized successfully")

    return pipeline, config


def main():
    parser = argparse.ArgumentParser(
        description="RAG OCR System - Retrieve and Generate with OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query the knowledge base
  python cli/main.py --config config/config.yaml --query "What is in the document?"

  # Ingest a PDF
  python cli/main.py --config config/config.yaml --ingest-pdf data/sample.pdf

  # Ingest an image
  python cli/main.py --config config/config.yaml --ingest-image data/sample.jpg

  # List statistics
  python cli/main.py --config config/config.yaml --stats
        """,
    )

    parser.add_argument("--config", default="config/config.yaml", help="Path to config file")
    parser.add_argument("--query", help="Query the knowledge base")
    parser.add_argument("--stream", action="store_true", help="Stream the response")
    parser.add_argument("--ingest-image", help="Ingest an image file")
    parser.add_argument("--ingest-pdf", help="Ingest a PDF file")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--clear", action="store_true", help="Clear knowledge base")
    parser.add_argument("--list-docs", action="store_true", help="List all documents")

    args = parser.parse_args()

    try:
        pipeline, config = create_pipeline(args.config)

        if args.query:
            print("\n" + "=" * 60)
            print("QUERY:", args.query)
            print("=" * 60)
            if args.stream:
                print("\nResponse (streaming):")
                for chunk in pipeline.query(args.query, use_stream=True):
                    print(chunk, end="", flush=True)
                print()
            else:
                response = pipeline.query(args.query, use_stream=False)
                print("\nResponse:")
                print(response)
            print("=" * 60 + "\n")

        elif args.ingest_image:
            if not os.path.exists(args.ingest_image):
                print(f"Error: Image file not found: {args.ingest_image}")
                sys.exit(1)
            print(f"Ingesting image: {args.ingest_image}")
            doc_id = pipeline.ingest_image(args.ingest_image)
            print(f"✓ Ingested successfully (ID: {doc_id})")

        elif args.ingest_pdf:
            if not os.path.exists(args.ingest_pdf):
                print(f"Error: PDF file not found: {args.ingest_pdf}")
                sys.exit(1)
            print(f"Ingesting PDF: {args.ingest_pdf}")
            doc_id = pipeline.ingest_pdf(args.ingest_pdf)
            print(f"✓ Ingested successfully (ID: {doc_id})")

        elif args.stats:
            stats = pipeline.get_statistics()
            print("\n" + "=" * 60)
            print("RAG SYSTEM STATISTICS")
            print("=" * 60)
            for key, value in stats.items():
                print(f"{key:.<40} {value}")
            print("=" * 60 + "\n")

        elif args.list_docs:
            docs = pipeline.list_documents()
            print(f"\nTotal documents: {len(docs)}")
            if docs:
                print("\nDocument IDs:")
                for doc_id in docs[:20]:  # Show first 20
                    print(f"  - {doc_id}")
                if len(docs) > 20:
                    print(f"  ... and {len(docs) - 20} more")
            print()

        elif args.clear:
            confirm = input("Are you sure you want to clear the knowledge base? (yes/no): ")
            if confirm.lower() == "yes":
                pipeline.clear_knowledge_base()
                print("✓ Knowledge base cleared")
            else:
                print("Cancelled")

        else:
            parser.print_help()

    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
