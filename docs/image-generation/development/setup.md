# Development Setup

**Last Updated:** 2024-01-15  
**Audience:** Developers  
**Time Required:** 30 minutes

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Running Tests](#running-tests)
- [Development Workflow](#development-workflow)
- [Debugging](#debugging)
- [Common Issues](#common-issues)

## Prerequisites

### Required Software

```bash
# Python 3.10 or higher
python --version
# Expected: Python 3.10.x or higher

# pip (Python package manager)
pip --version

# Git
git --version
```

### Required Accounts/Access

1. **Cloudflare Workers** (Optional for testing)
   - Flux worker URL (or use provided default)
   - SDXL worker URL with API key

2. **LLM Provider** (Required)
   - OpenRouter API key OR
   - Google Gemini API key

3. **Telegram** (Required)
   - API ID and Hash from https://my.telegram.org
   - Phone number for userbot

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd sakaibot
```

### 2. Create Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Verify activation
which python
# Should point to venv/bin/python
```

### 3. Install Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(httpx|telethon|pydantic|pytest)"
```

### 4. Configure Environment

Create `.env` file:

```bash
# Copy example
cp .env.example .env

# Edit with your editor
nano .env
```

**Minimum Configuration:**

```env
# Telegram (Required)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE_NUMBER=+1234567890

# LLM Provider (Choose one)
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free

# Image Generation (Optional for testing)
FLUX_WORKER_URL=https://image-smoke-ad69.fa-ra9931143.workers.dev
SDXL_WORKER_URL=https://image-api.cpt-n3m0.workers.dev
SDXL_API_KEY=your_bearer_token_here
```

### 5. Verify Configuration

```bash
# Run configuration check
python -c "
from src.core.config import get_settings
config = get_settings()
print(f'Telegram: {\"✓\" if config.telegram_api_id else \"✗\"}')
print(f'LLM: {\"✓\" if config.is_ai_enabled else \"✗\"}')
print(f'Image Gen: {\"✓\" if config.is_image_generation_enabled else \"✗\"}')
"
```

Expected output:
```
Telegram: ✓
LLM: ✓
Image Gen: ✓
```

### 6. Create Required Directories

```bash
# Create directories
mkdir -p temp/images
mkdir -p logs
mkdir -p cache
mkdir -p data

# Verify
ls -la | grep -E "(temp|logs|cache|data)"
```

## Running Tests

### Run All Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Expected output:
# tests/unit/test_image_generator.py::test_flux_success ✓
# tests/unit/test_image_queue.py::test_add_request_flux ✓
# ... (40+ tests)
# ==================== 40 passed in 2.34s ====================
```

### Run Specific Test Files

```bash
# Image generator tests only
pytest tests/unit/test_image_generator.py -v

# Image queue tests only
pytest tests/unit/test_image_queue.py -v

# Prompt enhancer tests only
pytest tests/unit/test_prompt_enhancer.py -v

# Image handler tests only
pytest tests/unit/test_image_handler.py -v
```

### Run Specific Test

```bash
# Run single test by name
pytest tests/unit/test_image_queue.py::test_add_request_flux -v

# Run tests matching pattern
pytest -k "flux" -v
```

### Run with Coverage

```bash
# Install coverage tool
pip install pytest-cov

# Run with coverage report
pytest tests/unit/ --cov=src.ai --cov-report=html

# Open report
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Run Integration Tests

**Warning:** Requires real worker URLs and API keys

```bash
# Run integration tests (slow)
pytest tests/integration/ -v -m integration

# Skip integration tests (default)
pytest tests/unit/ -v -m "not integration"
```

### Test Markers

```python
# Available markers
@pytest.mark.integration  # Real API tests
@pytest.mark.slow         # Long-running tests
@pytest.mark.unit         # Unit tests (default)
```

## Development Workflow

### Typical Development Session

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Create feature branch
git checkout -b feature/my-feature

# 3. Make changes to code
# ... edit files ...

# 4. Run tests frequently
pytest tests/unit/ -v

# 5. Run specific tests for your changes
pytest tests/unit/test_image_queue.py -v

# 6. Check code quality (optional)
pylint src/ai/image_queue.py

# 7. Commit changes
git add src/ai/image_queue.py
git commit -m "feat: improve queue performance"

# 8. Push and create PR
git push origin feature/my-feature
```

### Code Style

Follow existing patterns:

```python
# Type hints
def add_request(self, model: str, prompt: str, user_id: int) -> str:
    """
    Add request to queue.
    
    Args:
        model: Model name ("flux" or "sdxl")
        prompt: User prompt
        user_id: Telegram user ID
        
    Returns:
        Request ID
    """
    pass

# Docstrings (Google style)
# Type hints for all parameters
# Clear variable names
# Comprehensive error handling
```

### File Organization

```
src/ai/
├── image_generator.py    # Worker HTTP client
├── image_queue.py        # Queue management
├── prompt_enhancer.py    # LLM enhancement
└── ...

tests/unit/
├── test_image_generator.py
├── test_image_queue.py
├── test_prompt_enhancer.py
└── ...
```

## Debugging

### Enable Debug Logging

```python
# In code
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via environment
export LOG_LEVEL=DEBUG
```

### Interactive Debugging

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or (Python 3.7+)
breakpoint()

# Run test
pytest tests/unit/test_image_queue.py::test_add_request_flux -v -s
```

### Print Debugging

```python
# Temporary debugging
print(f"DEBUG: request_id={request_id}, status={request.status}")

# Better: use logger
self._logger.debug(f"Processing request {request_id}")
```

### Check Queue State

```python
# In code or test
from src.ai.image_queue import image_queue

# Inspect state
print(f"Flux queue: {len(image_queue._flux_queue)}")
print(f"SDXL queue: {len(image_queue._sdxl_queue)}")
print(f"Flux processing: {image_queue._flux_processing}")
print(f"All requests: {image_queue._requests.keys()}")
```

### Mock External Services

```python
# In tests
from unittest.mock import AsyncMock, MagicMock

# Mock LLM
mock_processor = MagicMock()
mock_processor.execute_custom_prompt = AsyncMock(
    return_value="Enhanced prompt"
)

# Mock HTTP
with patch('httpx.AsyncClient.get') as mock_get:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'PNG_DATA'
    mock_get.return_value = mock_response
    
    # Test code here
```

### Common Debug Scenarios

#### Test Hanging

```python
# Symptom: Test never completes
# Cause: Queue state not cleared

# Fix: Clear state before test
@pytest.fixture
def clean_queue():
    from src.ai.image_queue import image_queue
    image_queue._flux_queue.clear()
    image_queue._sdxl_queue.clear()
    image_queue._requests.clear()
    image_queue._flux_processing = False
    image_queue._sdxl_processing = False
```

#### Import Errors

```python
# Symptom: ModuleNotFoundError
# Cause: Wrong Python path

# Fix: Run from project root
cd /path/to/sakaibot
pytest tests/unit/test_image_queue.py

# Or set PYTHONPATH
export PYTHONPATH=/path/to/sakaibot:$PYTHONPATH
```

## Common Issues

### Issue 1: Tests Fail with "Queue not empty"

**Symptom:**
```
AssertionError: Queue should be empty but has 2 items
```

**Cause:** Previous test didn't clean up queue state

**Solution:**
```python
# Add cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_queue():
    yield
    # Cleanup after each test
    from src.ai.image_queue import image_queue
    image_queue._flux_queue.clear()
    image_queue._sdxl_queue.clear()
    image_queue._requests.clear()
    image_queue._flux_processing = False
    image_queue._sdxl_processing = False
```

### Issue 2: httpx.Timeout ValueError

**Symptom:**
```
ValueError: httpx.Timeout must either include a default, or set all four parameters explicitly
```

**Cause:** Missing timeout parameters

**Solution:**
```python
# Include all four timeout parameters
timeout=httpx.Timeout(
    connect=30,
    read=120,
    write=120,
    pool=30
)
```

### Issue 3: Import Errors in Tests

**Symptom:**
```
ImportError: cannot import name 'image_queue'
```

**Cause:** Tests run from wrong directory

**Solution:**
```bash
# Always run from project root
cd /path/to/sakaibot
pytest tests/unit/
```

### Issue 4: Configuration Not Found

**Symptom:**
```
ConfigurationError: No configuration file found
```

**Cause:** `.env` file missing or in wrong location

**Solution:**
```bash
# Verify .env exists in project root
ls -la .env

# If missing, create it
cp .env.example .env
# Edit with your values
```

### Issue 5: Rate Limit in Tests

**Symptom:**
```
Tests fail with "Rate limit exceeded"
```

**Cause:** Real API calls hitting rate limits

**Solution:**
```python
# Mock rate limiter in tests
with patch('src.utils.rate_limiter.get_ai_rate_limiter') as mock_limiter:
    mock_limiter.return_value.check_rate_limit = AsyncMock(return_value=True)
    # Run test
```

## Next Steps

After setup:

1. **Explore Code:** Read [Code Structure](code-structure.md)
2. **Run Tests:** See [Testing Guide](testing.md)
3. **Make Changes:** Follow [Contributing Guide](contributing.md)
4. **Add Features:** See [Adding Models](adding-models.md)

## Getting Help

- **Documentation:** Check other docs in `docs/image-generation/`
- **Tests:** Look at test files for usage examples
- **Code:** Read implementation with comments
- **Issues:** Check GitHub issues or create new one

---

**Ready to develop?** → [Code Structure](code-structure.md)
