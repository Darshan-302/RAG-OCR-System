# Security Analysis & Findings

This document records security vulnerabilities found during code review and recommendations for fixes.

**Last Security Review**: 2026-08-26  
**Reviewed By**: Automated Security Agent  
**Review Scope**: `src/` directory (all Python modules)

---

## Executive Summary

- **Critical Findings**: 1 (Command Injection)
- **High Findings**: 2 (SSRF Vulnerabilities)
- **Medium Findings**: 2 (DoS, Path Traversal, Data Exposure)
- **Low Findings**: 4 (Information Disclosure, Resource Leak, Error Handling)

**Overall Risk Level**: HIGH (due to Command Injection in production path)

---

## Critical Issues

### ⚠️ CRITICAL: Command Injection via GPU Parameter

**Location**: `src/ocr/unlimited_ocr.py`, lines 38-39  
**Severity**: CRITICAL  
**CVSS Score**: 9.8 (Critical)

#### Vulnerability

```python
env = os.environ.copy()
env["CUDA_VISIBLE_DEVICES"] = self.gpu  # ← NO VALIDATION!
```

The `self.gpu` parameter from config (line 24) is not validated before being set as an environment variable.

#### Attack Scenario

If `config.yaml` contains:
```yaml
ocr:
  unlimited_ocr:
    gpu: "0 && rm -rf /"
```

The SGLang server process would execute arbitrary shell commands.

#### Risk

- Remote Code Execution (RCE)
- Complete system compromise
- Data loss, malware installation

#### Fix

**Priority**: IMMEDIATE

```python
def _validate_gpu(self):
    """Validate GPU parameter is safe."""
    valid_values = ["cpu", "all", "0", "1", "2", "3"]  # Extend as needed
    gpu_str = str(self.gpu).lower()
    
    # Allow single digit GPU IDs or special values
    if gpu_str in valid_values:
        return gpu_str
    
    # Allow comma-separated list of digits
    if all(part.isdigit() for part in gpu_str.split(",")):
        return self.gpu
    
    raise ValueError(f"Invalid GPU parameter: {self.gpu}")

# In __init__:
self.gpu = self._validate_gpu()
```

#### Test Case

```python
# Should fail
UnlimitedOCR({"unlimited_ocr": {"gpu": "0 && echo hacked"}})  # raises ValueError

# Should pass
UnlimitedOCR({"unlimited_ocr": {"gpu": "0"}})  # OK
UnlimitedOCR({"unlimited_ocr": {"gpu": "0,1"}})  # OK
```

---

## High-Severity Issues

### 🔴 HIGH: Server-Side Request Forgery (SSRF) - Ollama LLM

**Location**: `src/llm/ollama_llm.py`, lines 33, 57  
**Severity**: HIGH  
**CVSS Score**: 8.2 (High)

#### Vulnerability

```python
self.base_url = self.config.get("base_url", "http://localhost:11434")
response = requests.post(
    f"{self.base_url}/api/generate",  # ← URL not validated
    ...
)
```

No validation that `base_url` is safe. If configuration is user-controlled or loaded from untrusted source, attacker could redirect to internal services.

#### Attack Scenario

Config:
```yaml
llm:
  ollama:
    base_url: "http://internal-admin:9000"  # Attacker-controlled
```

The system would make requests to internal admin panel.

#### Impact

- Access to internal services
- Information disclosure
- Privilege escalation

#### Fix

```python
from urllib.parse import urlparse

def _validate_base_url(self, url: str) -> str:
    """Validate base_url is safe."""
    parsed = urlparse(url)
    
    # Only allow localhost for security
    allowed_hosts = ["localhost", "127.0.0.1", "::1"]
    if parsed.hostname not in allowed_hosts:
        raise ValueError(f"base_url must be localhost, got: {url}")
    
    # Only allow HTTP for localhost
    if parsed.scheme != "http":
        raise ValueError(f"base_url must use http scheme, got: {url}")
    
    return url

# In __init__:
self.base_url = self._validate_base_url(
    self.config.get("base_url", "http://localhost:11434")
)
```

---

### 🔴 HIGH: Server-Side Request Forgery (SSRF) - Ollama Embeddings

**Location**: `src/embeddings/ollama_embeddings.py`, line 22  
**Severity**: HIGH  
**CVSS Score**: 8.2 (High)

#### Vulnerability

```python
self.base_url = self.config.get("base_url", "http://localhost:11434")
response = requests.post(
    f"{self.base_url}/api/embeddings",  # ← URL not validated
    ...
)
```

Same SSRF vulnerability as LLM module.

#### Fix

Apply same validation as ollama_llm.py (see above).

---

## Medium-Severity Issues

### 🟠 MEDIUM: Denial of Service via Long Timeout

**Location**: `src/llm/ollama_llm.py`, lines 42, 66  
**Severity**: MEDIUM  
**CVSS Score**: 5.3 (Medium)

#### Vulnerability

```python
response = requests.post(
    ...,
    timeout=300,  # ← 5 minutes!
    stream=True,
)
```

Timeout is 300 seconds (5 minutes). Long timeout allows slow-rate DoS attacks.

#### Attack Scenario

- Attacker makes 50 requests to `/query`
- Each holds connection open for 5 minutes
- System runs out of resources after ~150 requests

#### Risk

- Denial of Service
- Resource exhaustion
- Process/memory leaks

#### Fix

```python
# Reasonable timeouts:
# - Connection: 10 seconds
# - Read: 30 seconds
# - Total: 60 seconds

response = requests.post(
    ...,
    timeout=(10, 30),  # (connect_timeout, read_timeout)
    stream=True,
)
```

---

### 🟠 MEDIUM: Path Traversal in Image Processing

**Location**: `src/ocr/unlimited_ocr.py`, line 99  
**Severity**: MEDIUM  
**CVSS Score**: 6.5 (Medium)

#### Vulnerability

```python
def extract_text(self, image_path: str) -> str:
    # No validation of image_path parameter
    # Could allow: ../../etc/passwd, symlink attacks
    with open(image_path, "rb") as f:
        ...
```

File paths not validated. Could allow reading arbitrary files.

#### Attack Scenario

```python
pipeline.extract_text("../../../../etc/shadow")
# Attempts to read system password file
```

#### Risk

- Arbitrary file read
- Information disclosure
- Access to sensitive data

#### Fix

```python
def extract_text(self, image_path: str) -> str:
    """Extract text from image."""
    # Validate and canonicalize path
    image_path = os.path.abspath(image_path)
    allowed_dir = os.path.abspath("./data")
    
    # Ensure path is within allowed directory
    if not image_path.startswith(allowed_dir):
        raise ValueError(f"Image path outside allowed directory: {image_path}")
    
    # Check file exists and is readable
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    with open(image_path, "rb") as f:
        ...
```

---

### 🟠 MEDIUM: Unencrypted Data Transmission

**Location**: `src/ocr/unlimited_ocr.py`, lines 25, 115-120  
**Severity**: MEDIUM  
**CVSS Score**: 6.5 (Medium)

#### Vulnerability

```python
self.server_url = "http://127.0.0.1:10000"  # HTTP, not HTTPS

# Images sent unencrypted:
response = requests.post(
    f"{self.server_url}/v1/chat/completions",  # HTTP
    json={
        "messages": [{"content": encode_image(image_path)}],
        ...
    },
)
```

Images are base64-encoded and sent over unencrypted HTTP.

#### Current Risk

- **Low**: Since it's localhost-only
- Mitigated by local-only design

#### Risk if Configuration Changes

- Image data could be intercepted
- Could enable man-in-the-middle attacks
- Violates privacy assumptions

#### Mitigation

1. Document that HTTP is only safe for localhost
2. Add validation that server_url must be localhost (same as SSRF fix)
3. Add warning if HTTPS configuration is attempted

```python
# Add this to _validate_base_url():
if "localhost" not in parsed.hostname and "127.0.0.1" not in parsed.hostname:
    logger.warning(
        "Using HTTP for non-localhost OCR server. "
        "Images may be transmitted unencrypted. "
        "Ensure network is secure or use HTTPS."
    )
```

---

## Low-Severity Issues

### 🟡 LOW: File Handle Leak in subprocess

**Location**: `src/ocr/unlimited_ocr.py`, lines 66-67  
**Severity**: LOW  
**CVSS Score**: 3.3 (Low)

#### Vulnerability

```python
log_file = open("./logs/sglang_server.log", "w", encoding="utf-8")
self.server_process = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT)
# If exception occurs here, log_file is never closed
```

File handle not closed if exception occurs. Can lead to resource leaks.

#### Fix

```python
log_file = None
try:
    log_file = open("./logs/sglang_server.log", "w", encoding="utf-8")
    self.server_process = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT)
    self.server_process._log_file = log_file
    return self.server_process
except Exception:
    if log_file:
        log_file.close()
    raise
```

Or use context manager:

```python
from contextlib import ExitStack

with ExitStack() as stack:
    log_file = stack.enter_context(open("./logs/sglang_server.log", "w"))
    self.server_process = subprocess.Popen(cmd, env=env, stdout=log_file)
    self.server_process._log_file = log_file
```

---

### 🟡 LOW: Information Disclosure via Exception Logging

**Locations**: 
- `src/llm/ollama_llm.py`, lines 48, 78
- `src/embeddings/ollama_embeddings.py`, line 34
- `src/ocr/unlimited_ocr.py`, lines 126-132

**Severity**: LOW  
**Type**: Information Disclosure

#### Vulnerability

```python
logger.error(f"Failed to generate response from Ollama: {e}")
```

Full exception objects logged. Could expose:
- Internal URLs
- Configuration details
- Stack traces
- Service names

#### Fix

```python
# Instead of:
logger.error(f"Failed to generate response from Ollama: {e}")

# Do:
if isinstance(e, requests.Timeout):
    logger.warning("LLM request timeout - server may be unresponsive")
elif isinstance(e, requests.ConnectionError):
    logger.warning("LLM connection failed - ensure Ollama is running")
else:
    logger.error(f"LLM error: {type(e).__name__}")  # Type only, not full exception
```

---

### 🟡 LOW: Silent Failure Masking

**Location**: `src/embeddings/ollama_embeddings.py`, line 49  
**Severity**: LOW  
**Type**: Maintainability/Reliability

#### Issue

```python
except Exception as e:
    logger.warning(f"Failed to embed text: {e}")
    embeddings.append(np.zeros(self.embedding_dimension, dtype=np.float32))
```

Returns zero vectors on failure. Caller can't distinguish between "text is empty" and "embedding failed".

#### Impact

- Search quality degrades silently
- Difficult to debug
- Could hide network issues

#### Better Approach

```python
except Exception as e:
    logger.error(f"Embedding failed for text segment")
    # Either:
    # 1. Raise to let caller handle
    raise ValueError("Embedding service failed") from e
    
    # Or 2. Return sentinel value caller can detect
    # return None  # Then check for None in caller
```

---

## Security Checklist

Use this checklist when reviewing or adding code:

- [ ] No hardcoded credentials or API keys
- [ ] All file paths validated and canonicalized
- [ ] All URL parameters validated against allowlist
- [ ] Environment variables sanitized (especially for subprocess)
- [ ] Error messages don't expose internal details
- [ ] All exceptions are caught and logged safely
- [ ] Timeouts are set to reasonable values
- [ ] File handles are properly closed
- [ ] No silent failures - errors are visible
- [ ] Configuration validated on load
- [ ] Sensitive data not logged
- [ ] Dependencies checked for vulnerabilities

---

## Remediation Plan

### Phase 1: CRITICAL (Do Immediately)

1. **GPU Parameter Validation** - `unlimited_ocr.py:38-39`
   - Add `_validate_gpu()` method
   - Validate in `__init__`
   - Add unit tests

### Phase 2: HIGH (Do This Sprint)

2. **SSRF Validation** - `ollama_llm.py:33`, `ollama_embeddings.py:22`
   - Add `_validate_base_url()` to both modules
   - Validate in `__init__`
   - Add unit tests
   - Document localhost-only design

### Phase 3: MEDIUM (Next Sprint)

3. **Path Traversal** - `unlimited_ocr.py:99`
4. **Timeout Reduction** - `ollama_llm.py:42, 66`
5. **Error Handling Improvements** - All modules

### Phase 4: LOW (Maintenance)

6. **Information Disclosure** - Remove full exceptions from logs
7. **File Handle Leak** - Use context managers
8. **Silent Failures** - Return sentinel or raise

---

## Testing Security Fixes

```bash
# Run security checks
python -m pytest tests/security/

# Test cases to add:
# - Invalid GPU parameters should raise ValueError
# - Invalid base_urls should raise ValueError
# - Path traversal attempts should raise ValueError
# - Timeouts should be reasonable
# - Error messages should not contain sensitive info
```

---

## References

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE-78**: Improper Neutralization of Special Elements (Command Injection)
- **CWE-918**: Server-Side Request Forgery (SSRF)
- **CWE-22**: Improper Limitation of a Pathname to a Restricted Directory

---

## For LLM Learning

When implementing security fixes:

1. **Validation Pattern**: Always validate external input before use
2. **Principle of Least Privilege**: Restrict to localhost when possible
3. **Fail Secure**: Return meaningful errors, don't hide failures
4. **Defense in Depth**: Multiple validation layers
5. **Assume Breach**: Log for detectability, not for debugging

When adding new features:

- Check SECURITY.md for patterns
- Run security review before committing
- Update this document with decisions
- Consider OWASP and CWE guidelines

---

**Prepared By**: Automated Security Review Agent  
**Date**: 2026-08-26  
**Next Review**: After critical fixes are applied
