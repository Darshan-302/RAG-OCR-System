# Setup Guide

## Prerequisites

- Python 3.9+ 
- Ollama (https://ollama.ai)
- Git
- 8GB+ RAM recommended
- GPU (optional, for faster processing)

## Step 1: Install Ollama

### macOS
```bash
# Download from https://ollama.ai/download or use Homebrew
brew install ollama

# Start Ollama service
ollama serve
```

### Linux
```bash
curl https://ollama.ai/install.sh | sh
ollama serve
```

### Windows
Download installer from https://ollama.ai/download/windows

## Step 2: Pull Required Models

In a new terminal (while Ollama is running):

```bash
# LLM model (Qwen 3.8B - ~2.2GB)
ollama pull qwen:3.8b

# Embeddings model (Nomic Embed Text - ~274MB)
ollama pull nomic-embed-text
```

To verify models are installed:
```bash
ollama list
```

## Step 3: Clone and Setup Repository

```bash
# Navigate to your workspace
cd /Users/darshan/darshan-patel

# The RAG-OCR-System directory should already be created
cd RAG-OCR-System

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Step 4: Verify Installation

```bash
# Test Ollama connection
curl http://localhost:11434/api/tags

# Run CLI help
python cli/main.py --help

# Check statistics
python cli/main.py --config config/config.yaml --stats
```

Expected output should show:
- Total documents: 0
- Embedding dimension: 768
- Vector store type: ChromaVectorStore
- LLM model: qwen:3.8b
- OCR type: UnlimitedOCR

## Step 5: Test with Sample Files

### Option A: Using Docker

```bash
# Build and run
docker-compose up -d

# Test the system
docker-compose exec rag-ocr python cli/main.py --config config/config.yaml --stats

# Clean up
docker-compose down
```

### Option B: Local Python

```bash
# Create sample data directory
mkdir -p data/{input,output,documents}

# Test ingest (you need to provide a sample image/PDF)
python cli/main.py --config config/config.yaml --ingest-image data/sample.jpg

# Test query
python cli/main.py --config config/config.yaml --query "What is shown in the document?"
```

## Configuration Options

### Using Different OCR Engines

**Unlimited-OCR (Default - Recommended)**
```yaml
ocr:
  type: "unlimited_ocr"
  unlimited_ocr:
    model_dir: "baidu/Unlimited-OCR"
    image_mode: "gundam"
    gpu: "0"
```

**Tesseract OCR (Lightweight)**
```yaml
ocr:
  type: "tesseract"
  tesseract:
    lang: "eng"
```

Install Tesseract:
```bash
# macOS
brew install tesseract

# Linux
sudo apt-get install tesseract-ocr

# Windows
Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Using Different Embeddings

**Ollama (Fast, Local)**
```yaml
embeddings:
  type: "ollama"
  ollama:
    model: "nomic-embed-text"  # Default, ~274MB
    base_url: "http://localhost:11434"
```

**Transformers (More Accurate)**
```yaml
embeddings:
  type: "transformers"
  transformers:
    model_name: "sentence-transformers/all-MiniLM-L6-v2"
    device: "cuda"  # or "cpu"
```

This will download the model on first use (~80MB).

### Using Different Vector Stores

**Chroma (Default, Easy)**
```yaml
vector_store:
  type: "chroma"
  chroma:
    persist_directory: "./data/chroma_db"
    collection_name: "ocr_documents"
```

**FAISS (Scalable)**
```yaml
vector_store:
  type: "faiss"
  faiss:
    index_path: "./data/faiss_index"
    dimension: 384  # Must match embedding dimension
```

### Adjusting LLM Parameters

```yaml
llm:
  type: "ollama"
  ollama:
    model: "qwen:3.8b"
    base_url: "http://localhost:11434"
    temperature: 0.7      # 0=deterministic, 1=random
    top_p: 0.9           # Nucleus sampling
    max_tokens: 2048     # Maximum response length
```

## Environment Variables

Create a `.env` file (optional):

```bash
# Ollama configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen:3.8b

# GPU configuration
CUDA_VISIBLE_DEVICES=0  # Which GPU to use

# Logging
LOG_LEVEL=INFO
```

## Troubleshooting

### Ollama Not Responding

```bash
# Check if service is running
pgrep ollama

# Start Ollama service
ollama serve

# In another terminal, test connection
curl -v http://localhost:11434/api/tags
```

### Model Download Timeout

Models are downloaded on first use. If timeout occurs:

```bash
# Manually pull models with progress
ollama pull qwen:3.8b
ollama pull nomic-embed-text

# Check downloaded models
ollama list
```

### Memory Issues

If you encounter out-of-memory errors:

1. **Reduce chunk size** in config (default: 512)
2. **Reduce batch size** for OCR
3. **Use lighter embeddings** model
4. **Switch to CPU** if using Transformers embeddings

### GPU Not Detected

```bash
# Check available GPUs
python -c "import torch; print(torch.cuda.is_available())"

# Set GPU in config
ocr:
  unlimited_ocr:
    gpu: "0"  # Change to appropriate GPU number
```

## Next Steps

1. **Process Documents**: Start ingesting PDFs and images
2. **Customize Config**: Adjust parameters based on your needs
3. **Scale Up**: Add more documents to your knowledge base
4. **Deploy**: Use Docker for production deployment

## Common Commands

```bash
# Activate environment
source venv/bin/activate

# Show available Ollama models
ollama list

# Pull a new model
ollama pull <model-name>

# Pull specific model version
ollama pull qwen:7b

# Stop Ollama service
pkill ollama

# View Ollama logs (macOS)
log stream --predicate 'process == "Ollama"'
```

## Performance Tuning

### For Fast Response Times
- Use Ollama embeddings (nomic-embed-text)
- Reduce chunk size to 256
- Set temperature to 0.3
- Use top_k_retrieval: 3

### For Accuracy
- Use Transformers embeddings (sentence-bert)
- Increase chunk size to 1024
- Set temperature to 0.7
- Use top_k_retrieval: 10

### For Large Document Sets
- Use FAISS vector store
- Increase chunk_overlap
- Use batch processing

## Support

For detailed documentation, see:
- README.md - Overview and features
- config/config.yaml - Configuration reference
- cli/main.py - CLI options and examples
