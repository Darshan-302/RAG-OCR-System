# Guidelines for Working with Claude & LLMs on RAG-OCR-System

This document provides guidelines for Claude (or other LLMs) working on this codebase. It documents coding standards, architectural patterns, and project-specific conventions.

---

## Project Identity

**Name**: RAG-OCR-System  
**Purpose**: Retrieval-Augmented Generation system with local OCR and LLM inference  
**Core Values**:
- Local-first (no cloud dependencies)
- Modular architecture (pluggable components)
- Configuration-driven (YAML-based)
- Security-conscious (validate all inputs)
- Well-documented (for humans and LLMs)

---

## Code Standards

### Python Style

- **Target**: Python 3.9+
- **Style Guide**: PEP 8
- **Type Hints**: Required for all function signatures
- **Docstrings**: Only when non-obvious (prefer clear code over comments)
- **Line Length**: 120 characters max

### Module Structure

```
src/
├── [component]/
│   ├── __init__.py       # Export public interfaces
│   ├── base.py          # Abstract base class
│   ├── [impl]_*.py      # Concrete implementations
│   └── _utils.py        # Private helpers (if needed)
```

### Naming Conventions

```python
# Classes: PascalCase + component suffix
class OllamaLLM:
class ChromaVectorStore:
class UnlimitedOCR:

# Functions: snake_case
def extract_text(image_path: str) -> str:
def search(query: str, k: int = 5) -> list[dict]:

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
CHUNK_SIZE = 512

# Private: _leading_underscore
def _validate_url(url: str) -> str:
```

### Imports

```python
# Order: stdlib, third-party, local
import json
import os
from typing import Optional

import requests
import numpy as np

from .base import OCRBase
```

---

## Architectural Patterns

### 1. Abstract Base Classes

**Pattern**: Every component family has an abstract base.

```python
# src/ocr/base.py
from abc import ABC, abstractmethod

class OCRBase(ABC):
    def __init__(self, config: dict):
        self.config = config
    
    @abstractmethod
    def extract_text(self, image_path: str) -> str:
        """Extract text from image."""
        pass
```

**Why**: 
- Defines contract
- Allows multiple implementations
- Makes testing easier
- Enables configuration-driven selection

**When Adding New Component**:
- Create `base.py` with abstract class
- Implement concrete classes
- Register in `__init__.py`
- Add config example

### 2. Configuration-Driven Design

**Pattern**: All settings come from config dict or `config.yaml`, never hardcoded except defaults in class.

```python
class MyComponent(BaseComponent):
    def __init__(self, config: dict):
        # Don't do this:
        # self.timeout = 300
        
        # Do this instead:
        self.config = config.get("my_component", {})
        self.timeout = self.config.get("timeout", 300)  # Default in code
```

**Why**:
- No code changes to switch models
- Different configs for different environments
- Easy A/B testing

**Guidelines**:
- Define defaults in component __init__
- Document all config options
- Validate config on load
- Never hardcode credentials

### 3. Error Handling Pattern

**Pattern**: Graceful degradation with specific exception types.

```python
def extract_text(self, image_path: str) -> str:
    for attempt in range(MAX_RETRIES):
        try:
            # Operation
            return result
        except requests.Timeout:
            if attempt < MAX_RETRIES - 1:
                time.sleep(3 * (attempt + 1))
                continue
            logger.error("Max retries exceeded")
            raise
        except FileNotFoundError:
            logger.error(f"Image not found: {image_path}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}")
            raise
```

**Why**:
- Distinguishes between error types
- Retries transient failures
- Fails fast on permanent errors
- Logs for debugging

**Guidelines**:
- Don't swallow exceptions silently
- Log error context, not full traceback
- Retry only network failures
- Fail fast on validation errors

### 4. Logging Pattern

**Pattern**: Structured logging with clear levels.

```python
logger = logging.getLogger(__name__)

# Different levels for different purposes:
logger.debug(f"Processing image: {image_path}")      # Development
logger.info(f"Extracted {len(text)} chars from OCR")  # User-facing
logger.warning("Ollama timeout, retrying...")         # Recoverable issue
logger.error("Failed after 3 retries: {error}")       # Operation failed
```

**Why**:
- Debugging without code changes
- Tracking important events
- Distinguishing severity levels

**Guidelines**:
- INFO: User-visible state changes
- WARNING: Something unexpected but recoverable
- ERROR: Operation failed but system continues
- DEBUG: Development/troubleshooting only
- NEVER log credentials, API keys, sensitive data

---

## When Adding Features

### Step 1: Check DECISIONS.md

Read relevant ADRs to understand design philosophy. Key ADRs:
- **ADR-001**: Modular component architecture
- **ADR-002**: Configuration-driven design
- **ADR-003**: Local-first, no cloud
- **ADR-004**: Chunking strategy

### Step 2: Plan Architecture

Answer these questions:

1. **Is this a new component type?**
   - Create abstract base class
   - Define interface/contract
   - Add to config

2. **Is this extending existing component?**
   - Extend base class
   - Follow naming pattern
   - Add to config

3. **Is this modifying RAG logic?**
   - Check ADR-004 (chunking)
   - Maintain backward compatibility
   - Update documentation

### Step 3: Implement

Use these patterns:

```python
# Pattern: New Component Implementation
class MyNewOCR(OCRBase):
    def __init__(self, config: dict):
        super().__init__(config)
        self.config = config.get("my_new_ocr", {})
        self.model = self.config.get("model", "default-model")
        self.timeout = self.config.get("timeout", 30)
    
    def extract_text(self, image_path: str) -> str:
        """Extract text from image using my method."""
        try:
            # Implementation
            return text
        except Exception as e:
            logger.error(f"Failed to extract text: {type(e).__name__}")
            raise
    
    def extract_text_with_metadata(self, image_path: str) -> dict:
        """Extract text with metadata."""
        text = self.extract_text(image_path)
        return {
            "text": text,
            "image_path": image_path,
            "method": "my_new_ocr",
        }
    
    def process_pdf(self, pdf_path: str, output_dir: Optional[str] = None) -> dict:
        """Process PDF document."""
        # Implementation
        return {"pages": [...]}
```

### Step 4: Validate & Test

- [ ] All functions have type hints
- [ ] Config is validated on load
- [ ] Errors are logged (not silent)
- [ ] Timeouts are set
- [ ] No hardcoded paths/credentials
- [ ] Documentation updated

### Step 5: Document

Update these files:
- `DECISIONS.md` - Add ADR if new pattern
- `config/config.yaml` - Add config example
- `README.md` - Mention if user-facing
- Function docstrings - Explain behavior
- `SECURITY.md` - Any security implications

---

## When Fixing Bugs

### Step 1: Understand Root Cause

- [ ] Read full error message
- [ ] Check logs for context
- [ ] Understand data flow
- [ ] Identify which component is wrong

### Step 2: Check SECURITY.md

If security-related:
- [ ] Read relevant section in SECURITY.md
- [ ] Follow recommended fix pattern
- [ ] Add validation/sanitization
- [ ] Document in security findings

### Step 3: Implement Fix

- [ ] Minimal change (don't refactor unrelated code)
- [ ] Add unit test for bug
- [ ] Verify error message is helpful
- [ ] Check for similar issues elsewhere

### Step 4: Document

- [ ] Update docstring if behavior changed
- [ ] Add comment only if "why" is non-obvious
- [ ] Update DECISIONS.md if changing pattern
- [ ] Update SECURITY.md if security-related

---

## When Reviewing Code

Use this checklist:

**Correctness**:
- [ ] All exceptions handled
- [ ] All resources freed (file handles, connections)
- [ ] No off-by-one errors
- [ ] Null/None checks where needed
- [ ] Type hints correct

**Security** (check SECURITY.md):
- [ ] Input validation (file paths, URLs, parameters)
- [ ] No credential exposure in logs
- [ ] Error messages safe (no internal details)
- [ ] Timeouts set appropriately
- [ ] No command injection risks

**Style**:
- [ ] Follows PEP 8
- [ ] Naming consistent
- [ ] Type hints present
- [ ] Docstrings only when needed
- [ ] Imports organized

**Documentation**:
- [ ] Related ADRs updated
- [ ] Config examples added
- [ ] User-facing changes in README
- [ ] Comments explain "why" not "what"

---

## File Organization

### Adding a New Component

If adding a new OCR provider:

```
src/ocr/
├── __init__.py              # Add: from .my_ocr import MyOCR
├── base.py                  # (no change)
├── unlimited_ocr.py         # (existing)
├── tesseract_ocr.py         # (existing)
└── my_ocr.py               # NEW: implement MyOCR(OCRBase)

config/config.yaml           # Update: add my_ocr section

cli/main.py                  # Update: handle new type in create_ocr()

README.md                    # Update: list as available option

DECISIONS.md                 # Update: ADR-001 if new pattern
```

### Config File Format

When adding config section:

```yaml
# All sections follow this pattern:
[component_name]:
  type: "implementation_name"        # Which implementation to use
  [implementation_name]:              # Config for that implementation
    param1: "value"
    param2: 123
  [other_implementation]:             # Other options available
    param1: "value"

# Example:
ocr:
  type: "unlimited_ocr"
  unlimited_ocr:
    model_dir: "baidu/Unlimited-OCR"
    image_mode: "gundam"
  tesseract:
    lang: "eng"
```

---

## Development Workflow

### Before Starting

1. Read DECISIONS.md (relevant ADRs)
2. Check SECURITY.md (for security-related work)
3. Read related code in `src/`
4. Understand data flow

### While Coding

1. Follow patterns in existing code
2. Add type hints
3. Log important events
4. Validate all inputs
5. Handle all errors explicitly

### Before Committing

1. Run type checker: `mypy src/` (when set up)
2. Check security issues (SECURITY.md)
3. Update documentation
4. Test the change manually
5. Verify config examples work

### Commit Message

```
[Component] Brief description of change

- Specific change 1
- Specific change 2
- Reference to ADR if architectural

If fixing security issue from SECURITY.md:
Fixes: [Issue title]
```

---

## Special Cases

### Adding LLM Provider

1. Create `src/llm/[provider]_llm.py`
2. Extend `LLMBase`
3. Implement `generate()` and `generate_stream()`
4. Validate base_url (SSRF protection)
5. Set reasonable timeouts
6. Add to config/config.yaml
7. Update cli/main.py `create_llm()`

### Adding Vector Store

1. Create `src/vector_store/[provider].py`
2. Extend `VectorStoreBase`
3. Implement all abstract methods
4. Handle persistence (save/load)
5. Add to config/config.yaml
6. Update cli/main.py

### Adding Custom Embeddings

1. Create `src/embeddings/[provider]_embeddings.py`
2. Extend `EmbeddingsBase`
3. Implement `embed_text()` and `embed_texts()`
4. Cache embedding dimension
5. Add to config/config.yaml

---

## Common Patterns to Reuse

### Retry Loop

```python
for attempt in range(MAX_RETRIES):
    try:
        result = do_operation()
        return result
    except NetworkError:
        if attempt < MAX_RETRIES - 1:
            wait_time = 3 * (attempt + 1)
            time.sleep(wait_time)
            continue
        raise
```

### Config Validation

```python
def __init__(self, config: dict):
    self.config = config.get("component_name", {})
    
    # Required parameters
    self.required_param = self.config.get("required_param")
    if not self.required_param:
        raise ValueError("required_param not configured")
    
    # Optional with defaults
    self.optional_param = self.config.get("optional_param", "default_value")
```

### Resource Management

```python
from contextlib import ExitStack

with ExitStack() as stack:
    file1 = stack.enter_context(open("file1"))
    file2 = stack.enter_context(open("file2"))
    # Both files auto-closed on exit
```

---

## LLM Learning Guidelines

To improve future LLM contributions, this project documents:

1. **Why decisions matter**: DECISIONS.md explains trade-offs
2. **Security concerns**: SECURITY.md lists vulnerabilities and patterns
3. **Configuration philosophy**: ADR-002 explains why everything is configurable
4. **Component architecture**: ADR-001 explains modular design
5. **Code patterns**: This file (CLAUDE.md)

When making changes:

- **Reference relevant ADRs**
- **Check SECURITY.md** for patterns
- **Update DECISIONS.md** if changing patterns
- **Document the "why"** in code comments
- **Think about edge cases** (errors, timeouts, invalid input)

---

## Questions to Ask Before Contributing

1. **Does this break existing behavior?** (Check backward compatibility)
2. **Have I validated all inputs?** (Check SECURITY.md)
3. **Are errors logged clearly?** (Check logging pattern)
4. **Is this configurable?** (Check ADR-002)
5. **Should I update DECISIONS.md?** (Check if new pattern)
6. **Is this documented?** (README, docstrings, comments)

---

## Resources

- **Architecture**: DECISIONS.md
- **Security**: SECURITY.md
- **Setup**: SETUP.md
- **Features**: README.md
- **Project Structure**: PROJECT_SUMMARY.md

---

**Version**: 1.0  
**Last Updated**: 2026-08-26  
**Maintained By**: Project Contributors  
**For**: Claude and other LLMs contributing to this project
