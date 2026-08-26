# Architecture Decision Records (ADR)

This document records architectural decisions made in the RAG OCR System. Each entry captures the decision, rationale, trade-offs, and guidelines for future changes.

**For LLM Learning**: Read this file to understand the design philosophy, constraints, and decision patterns. When making changes, reference relevant ADRs and update this file if introducing new patterns or changing existing decisions.

---

## ADR-001: Modular Component Architecture

**Date**: 2026-08-26  
**Status**: Accepted  
**Priority**: High

### Decision

Use abstract base classes with pluggable implementations for all major components (OCR, Embeddings, Vector Store, LLM). Each component is independent and configurable via YAML.

### Rationale

- **Extensibility**: New models can be added without modifying existing code
- **Testing**: Each component can be tested independently
- **Configuration-Driven**: Users can switch implementations without code changes
- **Decoupling**: Reduces interdependencies between components
- **Scalability**: Easy to add new backends (e.g., new vector stores)

### Components

```
┌─── OCRBase ─────────────────┐
│ └─ UnlimitedOCR (default)   │
│ └─ TesseractOCR             │
│ └─ Custom (user extension)  │
└─────────────────────────────┘

┌─── EmbeddingsBase ──────────┐
│ └─ OllamaEmbeddings (def)   │
│ └─ TransformersEmbeddings   │
│ └─ Custom (user extension)  │
└─────────────────────────────┘

┌─── VectorStoreBase ─────────┐
│ └─ ChromaVectorStore (def)  │
│ └─ FaissVectorStore         │
│ └─ Custom (user extension)  │
└─────────────────────────────┘

┌─── LLMBase ─────────────────┐
│ └─ OllamaLLM (default)      │
│ └─ Custom (user extension)  │
└─────────────────────────────┘
```

### Trade-offs

| Aspect | Pro | Con |
|--------|-----|-----|
| **Abstraction** | Clean interfaces | More boilerplate code |
| **Flexibility** | Easy to extend | Multiple implementations to maintain |
| **Performance** | No overhead (direct calls) | Slight indirection |
| **Learning curve** | Clear patterns | More files to understand |

### Implementation Guidelines

1. **When Adding New Component Type**:
   - Create abstract base class in `src/[component]/base.py`
   - Define interface with required methods
   - Implement concrete classes with `[Name][Component].py`
   - Update `__init__.py` to export

2. **When Adding New Implementation**:
   - Extend the component's base class
   - Implement all abstract methods
   - Add configuration section to `config/config.yaml`
   - Update CLI to support the new implementation

3. **Base Class Guidelines**:
   - Use `@abstractmethod` decorator
   - Document expected behavior in docstrings
   - Define error handling contract
   - Include type hints

### Example: Adding Custom OCR

```python
from src.ocr.base import OCRBase

class MyCustomOCR(OCRBase):
    def __init__(self, config: dict):
        super().__init__(config)
        self.config = config.get("my_custom_ocr", {})
    
    def extract_text(self, image_path: str) -> str:
        # Implementation
        pass
    
    def extract_text_with_metadata(self, image_path: str) -> dict:
        # Implementation
        pass
    
    def process_pdf(self, pdf_path: str, output_dir: Optional[str] = None) -> dict:
        # Implementation
        pass
```

---

## ADR-002: Configuration-Driven Design

**Date**: 2026-08-26  
**Status**: Accepted  
**Priority**: High

### Decision

All settings are defined in `config/config.yaml`. No hardcoded defaults except in component classes. Configuration controls:
- Which components to use
- Component-specific parameters
- RAG pipeline behavior
- Data paths and logging

### Rationale

- **No code changes needed** to switch models or parameters
- **Reproducibility**: Same config produces same behavior
- **Multi-user**: Different users can have different configs
- **Easy A/B testing**: Compare by changing config
- **Production-ready**: Configuration management is scalable

### Structure

```yaml
ocr:
  type: "unlimited_ocr"           # Which implementation
  unlimited_ocr: {...}            # Component-specific config
  tesseract: {...}                # Other implementations

embeddings:
  type: "ollama"
  ollama: {...}
  transformers: {...}

vector_store:
  type: "chroma"
  chroma: {...}
  faiss: {...}

llm:
  type: "ollama"
  ollama: {...}

rag:
  chunk_size: 512
  chunk_overlap: 50
  top_k_retrieval: 5

logging:
  level: "INFO"
  file: "./logs/rag_system.log"
```

### Configuration Hierarchy

1. **Defaults**: Component class defaults
2. **Config File**: `config/config.yaml` overrides defaults
3. **Environment Variables**: Can override config file (future enhancement)
4. **Runtime Parameters**: CLI arguments override everything (future enhancement)

### Guidelines

1. **No Magic Numbers**: Define all parameters in config
2. **Sensible Defaults**: Config file should have working defaults
3. **Clear Documentation**: Every config option explained in file
4. **Type Safety**: Validate config types in components
5. **Versioning**: Document config version for compatibility

---

## ADR-003: Local-First, No Cloud Dependencies

**Date**: 2026-08-26  
**Status**: Accepted  
**Priority**: High

### Decision

All LLM inference happens locally via Ollama. No external API calls to cloud services. Data stays on user's machine.

### Rationale

- **Privacy**: No data sent to external servers
- **Cost**: No API costs or rate limiting
- **Control**: User controls all models and parameters
- **Offline**: Works without internet after model download
- **Compliance**: Meets data residency requirements

### Current Implementation

- OCR: Local SGLang server (Unlimited-OCR)
- LLM: Local Ollama (Qwen 3.8B)
- Embeddings: Local Ollama or Transformers
- Vector Store: Local persistence

### Future Considerations

- Support for quantized models (GGUF format)
- Model fine-tuning capabilities
- Distributed/multi-GPU inference

### APIs That Call External Services

Currently **NONE**. All HTTP calls are to localhost:

- `http://localhost:11434` - Ollama
- `http://127.0.0.1:10000` - SGLang (OCR)

### Guidelines

1. **No External APIs**: If feature needs cloud service, evaluate local alternative
2. **Configuration Over Integration**: Make external options configurable, default to local
3. **Document Data Flow**: Mark where data flows and confirm it doesn't leave machine

---

## ADR-004: Chunking Strategy for Document Processing

**Date**: 2026-08-26  
**Status**: Accepted  
**Priority**: Medium

### Decision

- Fixed-size chunking with overlap
- Default chunk size: 512 tokens/characters
- Default overlap: 50 tokens/characters
- Apply chunking after OCR extraction
- Store chunk index and total in metadata

### Rationale

- **Semantic Boundaries**: Fixed size respects LLM token limits
- **Overlap**: Prevents losing information at chunk boundaries
- **Metadata**: Allows reassembly and source tracking
- **Configurable**: Users can adjust for their use case

### Chunking Process

```
Input PDF/Image
    ↓
OCR Extraction → Full Text
    ↓
Text Splitting → Chunks (512 chars, 50 overlap)
    ↓
Embed Each Chunk
    ↓
Store: {id, text, chunk_index, total_chunks, source}
```

### Configuration

```yaml
rag:
  chunk_size: 512          # Characters per chunk
  chunk_overlap: 50        # Overlap between chunks
  top_k_retrieval: 5       # How many chunks to retrieve
```

### Trade-offs

| Aspect | Fixed Size | Smart Boundaries |
|--------|-----------|-----------------|
| **Complexity** | Simple | Complex |
| **Consistency** | Predictable | Variable |
| **Quality** | Good | Better |
| **Speed** | Fast | Slower |

### Future Enhancements

- Smart boundary detection (sentence/paragraph based)
- Adaptive chunk sizing based on document type
- Hierarchical chunking (section → paragraph → sentence)

---

## ADR-005: Error Handling and Resilience

**Date**: 2026-08-26  
**Status**: Accepted  
**Priority**: Medium

### Decision

- Graceful degradation: Partial failures don't stop entire pipeline
- Retry logic: Up to 3 retries with exponential backoff for network calls
- Logging: All errors logged with context
- User-facing: Errors returned in response, not exceptions
- Transactions: Vector store additions are atomic

### Implementation

```python
# Pattern: Retry with exponential backoff
for attempt in range(MAX_RETRIES):
    try:
        result = api_call()
        return result
    except NetworkError:
        if attempt < MAX_RETRIES - 1:
            wait_time = 3 * (attempt + 1)
            sleep(wait_time)
        else:
            logger.error(f"Failed after {MAX_RETRIES} retries")
            raise
```

### Guidelines

1. **Don't Swallow Errors**: Log before returning empty result
2. **Meaningful Messages**: Include context (what operation, which file)
3. **Retry Only Network**: Don't retry validation errors
4. **Fast Fail**: Don't retry if clearly won't succeed

---

## ADR-006: Logging and Observability

**Date**: 2026-08-26  
**Status**: Accepted  
**Priority**: Low

### Decision

- Use Python `logging` module
- Log level configurable in config
- Both console and file logging
- Structured logging format: timestamp - module - level - message

### Log Levels

- **DEBUG**: Detailed flow, variable values (development)
- **INFO**: Component initialization, operation completed
- **WARNING**: Recoverable issues, retries, non-critical failures
- **ERROR**: Operation failed, exception occurred
- **CRITICAL**: System failure, unrecoverable error

### Guidelines

1. **INFO**: User-visible state changes
2. **DEBUG**: Development and troubleshooting (disabled by default)
3. **WARNING**: Something might be wrong but doesn't stop execution
4. **ERROR**: Operation failed but system continues
5. **No Passwords**: Never log API keys, tokens, or credentials

---

## ADR-007: Testing Strategy (Planned)

**Date**: 2026-08-26  
**Status**: Planned  
**Priority**: Medium

### Decision (Future)

- Unit tests for each component
- Integration tests for RAG pipeline
- Mock external services (Ollama) in tests
- Test data in `tests/fixtures/`

### Guidelines (When Implementing)

1. Each component type gets unit tests
2. Full pipeline gets integration tests
3. Mock Ollama responses
4. Test both success and failure paths

---

## ADR-008: Documentation Strategy

**Date**: 2026-08-26  
**Status**: Accepted  
**Priority**: High

### Decision

- **README.md**: Feature overview and usage
- **SETUP.md**: Installation and configuration guide
- **QUICKSTART.md**: 5-minute quick start
- **DECISIONS.md**: This file (architecture and guidelines)
- **PROJECT_SUMMARY.md**: Project structure and components
- **SECURITY.md**: Security considerations and findings
- **Code Comments**: Minimal, only for non-obvious logic

### Audience

- **Users**: README, QUICKSTART, SETUP
- **Developers**: DECISIONS, PROJECT_SUMMARY, code
- **LLMs/Claude**: All documents, especially DECISIONS and PROJECT_SUMMARY

### Guidelines

1. **README**: What it does, main features, quick links
2. **SETUP**: Step-by-step installation
3. **QUICKSTART**: Get running in 5 minutes
4. **DECISIONS**: Why decisions were made, trade-offs
5. **Comments**: Only explain "why" not "what"

---

## Decision Tree for LLMs

When modifying or extending this codebase:

```
1. Is this a NEW feature or capability?
   ├─ Yes: Check ADR-001 (modular design)
   │       Create abstract base class if needed
   │       Add configuration section
   │       Document in DECISIONS.md
   │
   └─ No: Is this fixing an existing component?
          ├─ Yes: Check component's base class
          │       Maintain interface contract
          │       Update DECISIONS.md if changing behavior
          │
          └─ No: Are you changing RAG pipeline logic?
                 ├─ Yes: Check ADR-004 (chunking)
                 │       Ensure backward compatibility
                 │       Document new parameters
                 │
                 └─ No: Update relevant DECISION if changing
                        architectural assumptions

2. Before making changes:
   ├─ Read relevant ADRs
   ├─ Check CLAUDE.md if exists
   ├─ Run security review
   ├─ Document decision if new

3. After changes:
   ├─ Update DECISIONS.md
   ├─ Update configuration example
   ├─ Add logging statements
   ├─ Document in docstrings
```

---

## Template for New Decisions

When adding a new ADR:

```markdown
## ADR-XXX: [Decision Title]

**Date**: [Date]  
**Status**: [Proposed/Accepted/Deprecated]  
**Priority**: [High/Medium/Low]

### Decision
[What decision was made]

### Rationale
[Why this decision]

### Trade-offs
[What was given up]

### Guidelines
[How to implement this consistently]

### Future Considerations
[What might change]
```

---

## Status Summary

| ADR | Title | Status | Impact |
|-----|-------|--------|--------|
| 001 | Modular Components | Accepted | High |
| 002 | Configuration-Driven | Accepted | High |
| 003 | Local-First Design | Accepted | High |
| 004 | Chunking Strategy | Accepted | Medium |
| 005 | Error Handling | Accepted | Medium |
| 006 | Logging | Accepted | Low |
| 007 | Testing Strategy | Planned | Medium |
| 008 | Documentation | Accepted | High |

---

## How to Use This Document

1. **Before Contributing**: Read relevant ADRs
2. **Making Decisions**: Reference decision tree
3. **Adding Features**: Create new ADR
4. **Deprecating**: Mark ADR as deprecated, explain why
5. **For LLMs**: Read entire document to understand design philosophy

---

**Last Updated**: 2026-08-26  
**Maintained By**: Project Contributors
