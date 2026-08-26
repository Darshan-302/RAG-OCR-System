# Quick Start Guide

Get up and running with RAG OCR System in 5 minutes!

## 1. Prerequisites

Make sure you have Ollama installed and running:

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it:
ollama serve
```

## 2. Pull Models

In another terminal:

```bash
ollama pull qwen:3.8b
ollama pull nomic-embed-text
```

## 3. Install Python Dependencies

```bash
cd /Users/darshan/darshan-patel/RAG-OCR-System
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Verify Installation

```bash
python cli/main.py --config config/config.yaml --stats
```

Should output something like:
```
============================================================
RAG SYSTEM STATISTICS
============================================================
total_documents........................ 0
embedding_dimension................... 384
vector_store_type..................... ChromaVectorStore
llm_model.............................. qwen:3.8b
ocr_type.............................. UnlimitedOCR
============================================================
```

## 5. Test with Your First Query

Create a test image or PDF, then:

```bash
# Ingest an image
python cli/main.py --config config/config.yaml --ingest-image path/to/your/image.jpg

# Query it
python cli/main.py --config config/config.yaml --query "What is in this document?"
```

## Docker Option (Alternative)

Instead of local setup, use Docker:

```bash
docker-compose up -d

# Wait for services to start (20-30 seconds)

# Run commands
docker-compose exec rag-ocr python cli/main.py --config config/config.yaml --stats
```

## Configuration Files

Key configuration files to know:

- **config/config.yaml**: Main configuration for OCR, embeddings, vector store, and LLM
- **.env.example**: Environment variables template
- **requirements.txt**: Python package dependencies
- **docker-compose.yml**: Docker services configuration

## Common Use Cases

### Extract text from PDF
```bash
python cli/main.py --config config/config.yaml --ingest-pdf data/document.pdf
python cli/main.py --config config/config.yaml --query "What is the main topic?"
```

### Extract text from image
```bash
python cli/main.py --config config/config.yaml --ingest-image data/screenshot.png
python cli/main.py --config config/config.yaml --query "What does this image show?"
```

### Stream responses
```bash
python cli/main.py --config config/config.yaml --query "..." --stream
```

### View knowledge base stats
```bash
python cli/main.py --config config/config.yaml --stats
```

### List all documents
```bash
python cli/main.py --config config/config.yaml --list-docs
```

## Switching Between OCR Models

Edit `config/config.yaml`:

```yaml
# For Unlimited-OCR (Default, Accurate)
ocr:
  type: "unlimited_ocr"

# For Tesseract (Lightweight)
ocr:
  type: "tesseract"
```

## Switching Between Vector Stores

```yaml
# For Chroma (Default, Persistent)
vector_store:
  type: "chroma"

# For FAISS (Scalable)
vector_store:
  type: "faiss"
```

## Troubleshooting Quick Fixes

**Issue: "Connection refused" to Ollama**
```bash
# Make sure Ollama is running
ollama serve
```

**Issue: Models not found**
```bash
# Pull the models
ollama pull qwen:3.8b
ollama pull nomic-embed-text
ollama list  # Verify they're installed
```

**Issue: "No module named ..."**
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

**Issue: Out of memory**
- Edit config.yaml and reduce chunk_size to 256
- Or switch to lighter models

## Next Steps

1. Read **README.md** for full feature documentation
2. Read **SETUP.md** for detailed setup instructions
3. Explore **config/config.yaml** for all configuration options
4. Check **EXAMPLES.md** (coming soon) for advanced use cases

## Project Structure

```
RAG-OCR-System/
├── config/config.yaml        ← Customize settings here
├── cli/main.py              ← Run commands from here
├── src/                     ← Core modules (don't edit unless extending)
├── data/                    ← Your documents go here
├── requirements.txt         ← Python dependencies
├── Dockerfile              ← Docker image definition
├── docker-compose.yml      ← Docker Compose setup
├── README.md               ← Full documentation
├── SETUP.md               ← Detailed setup guide
└── QUICKSTART.md          ← This file
```

## API Usage (Python)

```python
from src.rag import RAGPipeline
from src.ocr import UnlimitedOCR
from src.embeddings import OllamaEmbeddings
from src.vector_store import ChromaVectorStore
from src.llm import OllamaLLM
import yaml

# Load configuration
with open("config/config.yaml") as f:
    config = yaml.safe_load(f)

# Create components
ocr = UnlimitedOCR(config["ocr"])
embeddings = OllamaEmbeddings(config["embeddings"])
vector_store = ChromaVectorStore(config["vector_store"], embeddings)
llm = OllamaLLM(config["llm"])

# Initialize pipeline
pipeline = RAGPipeline(ocr, embeddings, vector_store, llm, config)

# Use the pipeline
pipeline.ingest_pdf("path/to/document.pdf")
response = pipeline.query("Your question here")
print(response)
```

## Performance Tips

1. **Keep Ollama running** - Reduces startup time
2. **Use nomic-embed-text** - Faster embeddings
3. **Start small** - Test with one document first
4. **Monitor resources** - Watch GPU/CPU usage in docker-compose logs

## Getting Help

1. Check logs: `cat logs/rag_system.log`
2. Verify Ollama: `curl http://localhost:11434/api/tags`
3. Test Docker: `docker-compose logs`
4. Read full docs: `README.md` and `SETUP.md`

---

**Ready to start?** Run:
```bash
python cli/main.py --config config/config.yaml --stats
```

Good luck! 🚀
