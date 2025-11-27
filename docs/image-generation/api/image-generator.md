# ImageGenerator API Reference

**Last Updated:** 2024-01-15  
**Module:** `src.ai.image_generator`  
**Audience:** Developers

## Overview

`ImageGenerator` is the HTTP client responsible for communicating with Cloudflare Workers (Flux and SDXL) to generate images.

## Class Definition

```python
class ImageGenerator:
    """Handles image generation via Cloudflare Workers."""
```

**Location:** `src/ai/image_generator.py`  
**Lines of Code:** 259

## Constructor

### `__init__()`

```python
def __init__(self):
    """Initialize ImageGenerator with configuration."""
```

**Parameters:** None

**Initialization:**
- Loads configuration from `get_settings()`
- Initializes logger
- Sets `_http_client` to None (lazy initialization)

**Example:**
```python
from src.ai.image_generator import ImageGenerator

generator = ImageGenerator()
```

## Public Methods

### `generate_with_flux()`

```python
@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
async def generate_with_flux(self, enhanced_prompt: str) -> Tuple[bool, Optional[str], Optional[str]]
```

**Purpose:** Generate image using Flux worker

**Parameters:**
- `enhanced_prompt` (str): Enhanced prompt for image generation

**Returns:** `Tuple[bool, Optional[str], Optional[str]]`
- `success` (bool): True if generation successful
- `image_path` (str | None): Path to saved image file if successful
- `error_message` (str | None): Error description if failed

**Behavior:**
1. Makes GET request to Flux worker
2. Validates response status and content type
3. Saves image to temp directory
4. Returns success tuple or error tuple

**Retry Logic:**
- Retries on network errors and 5xx responses
- No retry on 4xx client errors
- Exponential backoff: 1s, 2s, 4s

**HTTP Status Handling:**
- 200: Success → save image
- 400: Bad request → return error
- 429: Rate limit → return error
- 500+: Server error → return error

**Example:**
```python
generator = ImageGenerator()

# Successful generation
success, path, error = await generator.generate_with_flux(
    "A beautiful cat sitting on a windowsill"
)
if success:
    print(f"Image saved to: {path}")
else:
    print(f"Error: {error}")

# Cleanup
await generator.close()
```

**Possible Errors:**
- `"Image generation request timed out"` - Timeout after 120s
- `"Rate limit exceeded..."` - HTTP 429
- `"Invalid prompt or request format"` - HTTP 400
- `"Service error..."` - HTTP 500+
- `"Network error during image generation..."` - Connection failed

### `generate_with_sdxl()`

```python
@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
async def generate_with_sdxl(self, enhanced_prompt: str) -> Tuple[bool, Optional[str], Optional[str]]
```

**Purpose:** Generate image using SDXL worker

**Parameters:**
- `enhanced_prompt` (str): Enhanced prompt for image generation

**Returns:** `Tuple[bool, Optional[str], Optional[str]]`
- Same as `generate_with_flux()`

**Behavior:**
1. Checks API key configuration
2. Makes POST request with Bearer auth
3. Validates response
4. Saves image
5. Returns result tuple

**Authentication:**
- Requires `SDXL_API_KEY` in configuration
- Uses Bearer token authentication
- Returns error if key missing

**HTTP Status Handling:**
- 200: Success → save image
- 400: Bad request → return error
- 401: Unauthorized → "Invalid API key"
- 405: Method not allowed → "Invalid request method"
- 429: Rate limit → return error
- 500+: Server error → return error

**Example:**
```python
generator = ImageGenerator()

# With valid API key
success, path, error = await generator.generate_with_sdxl(
    "A stunning landscape photograph"
)

if success:
    print(f"Image: {path}")
    # Use image
    Path(path).unlink()  # Cleanup
else:
    print(f"Error: {error}")
```

**Possible Errors:**
- `"SDXL API key not configured"` - Missing config
- `"SDXL API key invalid or missing"` - HTTP 401
- `"Invalid request method"` - HTTP 405
- Same errors as Flux for other cases

### `close()`

```python
async def close(self):
    """Close HTTP client."""
```

**Purpose:** Cleanup HTTP client resources

**Parameters:** None

**Returns:** None

**Behavior:**
- Closes httpx.AsyncClient if initialized
- Sets `_http_client` to None

**When to Call:**
- After all image generation complete
- Before application shutdown
- In finally blocks

**Example:**
```python
generator = ImageGenerator()
try:
    # Generate images
    await generator.generate_with_flux("prompt")
finally:
    await generator.close()  # Always cleanup
```

## Private Methods

### `_get_http_client()`

```python
def _get_http_client(self) -> httpx.AsyncClient
```

**Purpose:** Get or create HTTP client (lazy initialization)

**Returns:** `httpx.AsyncClient` instance

**Behavior:**
- Returns existing client if already created
- Creates new client with proper configuration
- Configures timeouts and limits

**Configuration:**
```python
httpx.AsyncClient(
    timeout=httpx.Timeout(
        connect=30,   # Connection timeout
        read=120,     # Read timeout
        write=120,    # Write timeout
        pool=30       # Pool timeout
    ),
    limits=httpx.Limits(
        max_keepalive_connections=5,
        max_connections=10
    ),
    follow_redirects=True
)
```

**Why Lazy:** Client created on first use, not in `__init__`

### `_make_flux_request()`

```python
async def _make_flux_request(self, prompt: str) -> httpx.Response
```

**Purpose:** Make GET request to Flux worker

**Parameters:**
- `prompt` (str): URL-encoded prompt

**Returns:** `httpx.Response`

**Raises:**
- `AIProcessorError` on timeout or network error

**HTTP Request:**
```http
GET https://worker.dev?prompt=<url_encoded_prompt>
```

**Example URL:**
```
https://worker.dev?prompt=A%20beautiful%20cat
```

### `_make_sdxl_request()`

```python
async def _make_sdxl_request(self, prompt: str) -> httpx.Response
```

**Purpose:** Make POST request to SDXL worker

**Parameters:**
- `prompt` (str): Prompt in JSON body

**Returns:** `httpx.Response`

**Raises:**
- `AIProcessorError` if API key not configured
- `AIProcessorError` on timeout or network error

**HTTP Request:**
```http
POST https://worker.dev
Authorization: Bearer <api_key>
Content-Type: application/json

{"prompt": "A beautiful cat"}
```

### `_save_image()`

```python
def _save_image(self, response_content: bytes, model_name: str) -> str
```

**Purpose:** Save image bytes to temporary file

**Parameters:**
- `response_content` (bytes): PNG/JPG image data
- `model_name` (str): "flux" or "sdxl"

**Returns:** str - Path to saved file

**Raises:**
- `AIProcessorError` on file I/O errors

**Filename Format:**
```
image_{model}_{request_id}_{timestamp}.png

Example:
image_flux_a1b2c3d4_1705334567.png
```

**Save Location:**
```
temp/images/image_flux_a1b2c3d4_1705334567.png
```

## Dependencies

### Internal
```python
from ..core.config import get_settings
from ..core.constants import (
    IMAGE_GENERATION_TIMEOUT,
    IMAGE_GENERATION_CONNECT_TIMEOUT,
    IMAGE_TEMP_DIR
)
from ..core.exceptions import AIProcessorError
from ..utils.logging import get_logger
from ..utils.retry import retry_with_backoff
```

### External
```python
import asyncio
import httpx
import uuid
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import quote
```

## Constants Used

```python
IMAGE_GENERATION_TIMEOUT = 120  # seconds
IMAGE_GENERATION_CONNECT_TIMEOUT = 30  # seconds
IMAGE_TEMP_DIR = "temp/images"
```

## Configuration

### Required Settings

**Flux:**
```python
flux_worker_url: str  # Worker URL
```

**SDXL:**
```python
sdxl_worker_url: str  # Worker URL
sdxl_api_key: str     # Bearer token
```

### Access Configuration

```python
from src.core.config import get_settings

config = get_settings()
print(config.flux_worker_url)
print(config.sdxl_worker_url)
print(config.sdxl_api_key)
```

## Error Handling

### Exception Types

**AIProcessorError** - Raised for all generation errors

**Caught Internally:**
- `httpx.TimeoutException` → converted to AIProcessorError
- `httpx.RequestError` → converted to AIProcessorError

**Error Categories:**

1. **Timeout Errors**
   ```python
   AIProcessorError("Image generation request timed out")
   ```

2. **Network Errors**
   ```python
   AIProcessorError(f"Network error during image generation: {e}")
   ```

3. **HTTP Errors**
   - Handled by checking response.status_code
   - Converted to user-friendly messages

### Return Tuple Pattern

```python
# Success
(True, "/path/to/image.png", None)

# Failure
(False, None, "Error message")
```

**Benefits:**
- No exceptions for expected failures
- Easy to check success
- Error message included

## Usage Patterns

### Basic Usage

```python
from src.ai.image_generator import ImageGenerator

async def generate_image():
    generator = ImageGenerator()
    try:
        success, path, error = await generator.generate_with_flux(
            "A beautiful landscape"
        )
        if success:
            # Use image at path
            print(f"Generated: {path}")
        else:
            print(f"Failed: {error}")
    finally:
        await generator.close()
```

### With Error Handling

```python
async def safe_generate():
    generator = ImageGenerator()
    try:
        success, path, error = await generator.generate_with_sdxl(prompt)
        
        if not success:
            # Handle specific errors
            if "api key" in error.lower():
                print("Check SDXL configuration")
            elif "rate limit" in error.lower():
                print("Wait before retrying")
            else:
                print(f"Unknown error: {error}")
            return None
        
        return path
    finally:
        await generator.close()
```

### Multiple Generations

```python
async def generate_multiple():
    generator = ImageGenerator()
    try:
        results = []
        for prompt in prompts:
            success, path, error = await generator.generate_with_flux(prompt)
            results.append((success, path, error))
        return results
    finally:
        await generator.close()
```

## Performance Characteristics

### Timing

**Flux:**
- Connection: <1s
- Generation: 5-10s
- Total: 5-11s typical

**SDXL:**
- Connection: <1s
- Generation: 10-15s
- Total: 10-16s typical

**With Retries:**
- Add 1-7s for retry delays if needed

### Memory

- HTTP client: ~5MB
- Per request: ~2-5MB (image buffer)
- Temp file: 2-10MB on disk

### Concurrency

- Single client instance can handle multiple concurrent requests
- Connection pooling (max 10 connections, 5 keepalive)
- Async/await allows efficient concurrent usage

## Testing

### Unit Tests

Located in `tests/unit/test_image_generator.py`

**Test Cases:**
- Successful generation (both models)
- HTTP error handling (400, 401, 429, 500)
- Network errors
- Timeout errors
- Content type validation
- File saving
- Retry logic

### Mocking

```python
from unittest.mock import patch, MagicMock
import pytest

@pytest.mark.asyncio
async def test_flux_success():
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/png"}
        mock_response.content = b'PNG_DATA'
        mock_get.return_value = mock_response
        
        generator = ImageGenerator()
        success, path, error = await generator.generate_with_flux("test")
        
        assert success is True
        assert path is not None
```

## Best Practices

### Always Close

```python
generator = ImageGenerator()
try:
    # Use generator
    pass
finally:
    await generator.close()  # Important!
```

### Handle Both Success and Failure

```python
success, path, error = await generator.generate_with_flux(prompt)

if success:
    # Use image
    process_image(path)
    # Cleanup
    Path(path).unlink()
else:
    # Handle error
    log_error(error)
```

### Cleanup Temp Files

```python
if success:
    try:
        # Use image
        send_to_user(path)
    finally:
        # Always cleanup
        Path(path).unlink(missing_ok=True)
```

### Check Configuration First

```python
from src.core.config import get_settings

config = get_settings()
if not config.is_image_generation_enabled:
    print("Image generation not configured")
    return

generator = ImageGenerator()
# Proceed with generation
```

---

**Related APIs:**
- [ImageQueue](image-queue.md)
- [PromptEnhancer](prompt-enhancer.md)
- [ImageHandler](image-handler.md)
