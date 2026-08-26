# RAG OCR System

A modular Retrieval-Augmented Generation (RAG) system for processing and querying documents using local OCR and LLM models. Built with Ollama for local model inference and support for multiple vector stores and embedding models.

## Features

- **Multiple OCR Engines**: Unlimited-OCR, Tesseract, EasyOCR, and PaddleOCR support
- **Local LLM Inference**: Powered by Ollama with Qwen 3.8B (configurable)
- **Flexible Embeddings**: Ollama embeddings or transformer-based embeddings (Sentence-BERT)
- **Multiple Vector Stores**: Chroma or FAISS for document retrieval
- **PDF & Image Support**: Process images and PDF documents
- **Configuration-Driven**: All settings in YAML config file
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Python CLI**: Simple command-line interface for all operations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG OCR Pipeline                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input (Images/PDFs)                                        │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────────┐                                   │
│  │   OCR Module        │ (Unlimited-OCR, Tesseract, etc.) │
│  └────────────┬────────┘                                   │
│               │                                              │
│               ▼                                              │
│  ┌─────────────────────────────┐                           │
│  │  Text Chunking & Processing │                           │
│  └────────────┬────────────────┘                           │
│               │                                              │
│               ▼                                              │
│  ┌─────────────────────────────┐                           │
│  │  Embeddings Module          │ (Ollama, Transformers)    │
│  └────────────┬────────────────┘                           │
│               │                                              │
│               ▼                                              │
│  ┌─────────────────────────────┐                           │
│  │  Vector Store               │ (Chroma, FAISS)           │
│  └─────────────────────────────┘                           │
│               │                                              │
│               ├─────────┐                                   │
│               │         │                                    │
│               ▼         ▼                                    │
│         Query  ◄──────  User                               │
│         │               │                                    │
│         ▼               │                                    │
│  ┌──────────────────────┐ │                                │
│  │  Retriever           │ │                                │
│  └──────────┬───────────┘ │                                │
│             │              │                                │
│             ▼              │                                │
│  ┌──────────────────────┐ │                                │
│  │  LLM (Qwen + Ollama) │ ◄────────────────────────────── │
│  └──────────┬───────────┘                                  │
│             │                                               │
│             ▼                                               │
│         Response                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Local Setup

1. **Clone the repository**
   ```bash
   cd RAG-OCR-System
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Ollama** (if not already installed)
   - Download from https://ollama.ai
   - Follow installation instructions for your OS

5. **Pull required models**
   ```bash
   # LLM model
   ollama pull qwen:3.8b
   
   # Embeddings model
   ollama pull nomic-embed-text
   ```

### Docker Setup

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

2. **Verify services are running**
   ```bash
   docker-compose ps
   ```

## Configuration

Edit `config/config.yaml` to customize:

- **OCR**: Choose between Unlimited-OCR, Tesseract, EasyOCR, or PaddleOCR
- **Embeddings**: Ollama or Transformer-based embeddings
- **Vector Store**: Chroma or FAISS
- **LLM**: Model name and parameters (temperature, top_p, etc.)
- **RAG**: Chunk size, overlap, retrieval parameters

Example configuration:

```yaml
ocr:
  type: "unlimited_ocr"
  unlimited_ocr:
    model_dir: "baidu/Unlimited-OCR"
    image_mode: "gundam"
    gpu: "0"

embeddings:
  type: "ollama"
  ollama:
    model: "nomic-embed-text"
    base_url: "http://localhost:11434"

vector_store:
  type: "chroma"
  chroma:
    persist_directory: "./data/chroma_db"
    collection_name: "ocr_documents"

llm:
  type: "ollama"
  ollama:
    model: "qwen:3.8b"
    base_url: "http://localhost:11434"
    temperature: 0.7
```

## Usage

### Command Line Interface

**Query the knowledge base**
```bash
python cli/main.py --config config/config.yaml --query "What is in the document?"
```

**Stream response**
```bash
python cli/main.py --config config/config.yaml --query "..." --stream
```

**Ingest a PDF**
```bash
python cli/main.py --config config/config.yaml --ingest-pdf data/sample.pdf
```

**Ingest an image**
```bash
python cli/main.py --config config/config.yaml --ingest-image data/sample.jpg
```

**Show statistics**
```bash
python cli/main.py --config config/config.yaml --stats
```

**List documents**
```bash
python cli/main.py --config config/config.yaml --list-docs
```

**Clear knowledge base**
```bash
python cli/main.py --config config/config.yaml --clear
```

### Python API

```python
from src.ocr import UnlimitedOCR
from src.embeddings import OllamaEmbeddings
from src.vector_store import ChromaVectorStore
from src.llm import OllamaLLM
from src.rag import RAGPipeline
import yaml

# Load config
with open("config/config.yaml") as f:
    config = yaml.safe_load(f)

# Create components
ocr = UnlimitedOCR(config["ocr"])
embeddings = OllamaEmbeddings(config["embeddings"])
vector_store = ChromaVectorStore(config["vector_store"], embeddings)
llm = OllamaLLM(config["llm"])

# Create pipeline
pipeline = RAGPipeline(ocr, embeddings, vector_store, llm, config)

# Ingest a PDF
pipeline.ingest_pdf("data/sample.pdf")

# Query
response = pipeline.query("What is the main topic?")
print(response)

# Stream response
for chunk in pipeline.query("...", use_stream=True):
    print(chunk, end="", flush=True)
```

## Docker Usage

### Run with Docker Compose

```bash
# Start services
docker-compose up -d

# Execute CLI commands
docker-compose exec rag-ocr python cli/main.py --config config/config.yaml --stats

# Ingest documents
docker-compose exec rag-ocr python cli/main.py --config config/config.yaml --ingest-pdf data/sample.pdf

# Query
docker-compose exec rag-ocr python cli/main.py --config config/config.yaml --query "Your question here"

# View logs
docker-compose logs -f rag-ocr
```

### Custom Docker Build

```bash
# Build image
docker build -t rag-ocr-system .

# Run container
docker run -it \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  --network host \
  rag-ocr-system \
  python cli/main.py --config config/config.yaml --query "Your question"
```

## Project Structure

```
RAG-OCR-System/
├── config/
│   └── config.yaml              # Configuration file
├── src/
│   ├── ocr/                     # OCR modules
│   │   ├── base.py
│   │   ├── unlimited_ocr.py
│   │   └── tesseract_ocr.py
│   ├── embeddings/              # Embeddings modules
│   │   ├── base.py
│   │   ├── ollama_embeddings.py
│   │   └── transformers_embeddings.py
│   ├── vector_store/            # Vector store modules
│   │   ├── base.py
│   │   ├── chroma.py
│   │   └── faiss.py
│   ├── llm/                     # LLM modules
│   │   ├── base.py
│   │   └── ollama_llm.py
│   └── rag/                     # RAG pipeline
│       └── pipeline.py
├── cli/
│   └── main.py                  # CLI interface
├── data/                        # Data directory (created at runtime)
├── logs/                        # Logs directory (created at runtime)
├── Dockerfile                   # Docker image definition
├── docker-compose.yml          # Docker Compose configuration
├── requirements.txt             # Python dependencies
├── .gitignore
└── README.md
```

## Troubleshooting

### Ollama Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama service
ollama serve
```

### GPU Issues with Unlimited-OCR

If you encounter GPU memory issues:

1. Adjust batch size in config
2. Use `--gpu` parameter to specify GPU device
3. Consider using CPU mode for smaller models

### Model Download

Models are automatically downloaded on first use. Ensure you have sufficient disk space.

## Advanced Configuration

### Custom OCR Models

Add custom OCR models by extending the `OCRBase` class:

```python
from src.ocr.base import OCRBase

class CustomOCR(OCRBase):
    def extract_text(self, image_path: str) -> str:
        # Your implementation
        pass
```

### Custom Embeddings

Similarly, extend `EmbeddingsBase` for custom embeddings:

```python
from src.embeddings.base import EmbeddingsBase

class CustomEmbeddings(EmbeddingsBase):
    def embed_text(self, text: str) -> np.ndarray:
        # Your implementation
        pass
```

## Performance Tips

1. **Chunk Size**: Adjust `chunk_size` in config for optimal performance
2. **Top-K Retrieval**: Increase `top_k_retrieval` for more context
3. **Embeddings**: Use `nomic-embed-text` (faster) or `sentence-transformers` (more accurate)
4. **Vector Store**: Use FAISS for large document collections
5. **GPU**: Enable GPU acceleration in config for faster OCR and embeddings

## License

This project is provided as-is for research and educational purposes.

## Contributing

Contributions are welcome! Please ensure:

1. Code follows existing style conventions
2. New modules extend appropriate base classes
3. Configuration changes are documented
4. Tests pass before submitting PRs

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review configuration examples
3. Check logs in `./logs/` directory
4. Verify all services are running with docker-compose

## Roadmap

- [ ] Web UI for document management
- [ ] Batch processing improvements
- [ ] Additional OCR models
- [ ] Support for more vector databases
- [ ] Fine-tuning capabilities
- [ ] Multi-language support
- [ ] Performance benchmarking suite
