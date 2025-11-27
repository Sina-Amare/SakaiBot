# Code Structure

**Last Updated:** 2024-01-15  
**Audience:** Developers  
**Purpose:** Understanding the codebase organization

## Table of Contents

- [Directory Structure](#directory-structure)
- [Module Breakdown](#module-breakdown)
- [File Responsibilities](#file-responsibilities)
- [Import Dependencies](#import-dependencies)
- [Code Patterns](#code-patterns)
- [Extension Points](#extension-points)

## Directory Structure

```
sakaibot/
├── src/
│   ├── ai/                          # AI and image generation
│   │   ├── __init__.py
│   │   ├── image_generator.py       # Worker HTTP client
│   │   ├── image_queue.py           # Queue management
│   │   ├── prompt_enhancer.py       # LLM enhancement
│   │   ├── processor.py             # Base AI processor
│   │   ├── prompts.py               # All LLM prompts
│   │   └── providers/               # LLM provider implementations
│   │       ├── openrouter.py
│   │       └── gemini.py
│   │
│   ├── telegram/                    # Telegram integration
│   │   ├── handlers/
│   │   │   ├── image_handler.py     # Image command handler
│   │   │   ├── ai_handler.py        # AI chat handler
│   │   │   └── ...
│   │   ├── client.py
│   │   └── utils.py
│   │
│   ├── core/                        # Core configuration
│   │   ├── config.py                # Pydantic settings
│   │   ├── constants.py             # Global constants
│   │   ├── settings.py              # Settings manager
│   │   └── exceptions.py            # Custom exceptions
│   │
│   └── utils/                       # Utilities
│       ├── error_handler.py         # Error handling
│       ├── rate_limiter.py          # Rate limiting
│       ├── retry.py                 # Retry logic
│       ├── validators.py            # Input validation
│       ├── metrics.py               # Metrics tracking
│       └── logging.py               # Logging setup
│
├── tests/
│   ├── unit/                        # Unit tests
│   │   ├── test_image_generator.py
│   │   ├── test_image_queue.py
│   │   ├── test_prompt_enhancer.py
│   │   └── test_image_handler.py
│   │
│   └── integration/                 # Integration tests
│       └── test_image_integration.py
│
├── docs/
│   └── image-generation/            # Feature documentation
│       ├── README.md
│       ├── user-guides/
│       ├── architecture/
│       ├── development/
│       ├── api/
│       ├── troubleshooting/
│       └── implementation/
│
├── scripts/                         # Utility scripts
│   ├── verify_image_generation.py   # Test real workers
│   └── test_sdxl.py                 # SDXL-specific tests
│
├── temp/                            # Temporary files
│   └── images/                      # Generated images (auto-deleted)
│
├── .env                             # Environment variables (gitignored)
├── .env.example                     # Example configuration
├── requirements.txt                 # Python dependencies
├── pytest.ini                       # Pytest configuration
└── README.md                        # Project README
```

## Module Breakdown

### `src/ai/` - AI and Image Generation

Core module for all AI-related functionality.

#### `image_generator.py` (259 lines)

**Purpose:** HTTP client for Cloudflare Workers

**Key Classes:**
- `ImageGenerator` - Main generator class

**Key Methods:**
```python
async def generate_with_flux(prompt: str) -> Tuple[bool, Optional[str], Optional[str]]
async def generate_with_sdxl(prompt: str) -> Tuple[bool, Optional[str], Optional[str]]
async def _make_flux_request(prompt: str) -> httpx.Response
async def _make_sdxl_request(prompt: str) -> httpx.Response
def _save_image(content: bytes, model: str) -> str
async def close() -> None
```

**Dependencies:**
- httpx (HTTP client)
- config (worker URLs, API keys)
- retry decorator
- logging

**Exports:**
```python
from src.ai.image_generator import ImageGenerator
```

#### `image_queue.py` (359 lines)

**Purpose:** Queue management with FIFO per model

**Key Classes:**
- `ImageStatus` - Enum for request status
- `ImageRequest` - Dataclass for request data
- `ImageQueue` - Queue manager (singleton)

**Key Methods:**
```python
def add_request(model: str, prompt: str, user_id: int) -> str
def try_start_processing(request_id: str, model: str) -> bool
def get_queue_position(request_id: str, model: str) -> Optional[int]
def mark_completed(request_id: str, image_path: str) -> None
def mark_failed(request_id: str, error: str) -> None
def get_request(request_id: str) -> Optional[ImageRequest]
def cleanup_request(request_id: str) -> None
```

**Global Instance:**
```python
image_queue = ImageQueue()  # Singleton
```

**Exports:**
```python
from src.ai.image_queue import (
    ImageStatus,
    ImageRequest,
    ImageQueue,
    image_queue  # Global instance
)
```

#### `prompt_enhancer.py` (99 lines)

**Purpose:** LLM-based prompt enhancement

**Key Classes:**
- `PromptEnhancer` - Enhancement wrapper

**Key Methods:**
```python
async def enhance_prompt(user_prompt: str) -> str
```

**Dependencies:**
- AIProcessor (for LLM calls)
- Prompts (enhancement prompts)
- Constants (max length)

**Exports:**
```python
from src.ai.prompt_enhancer import PromptEnhancer
```

#### `prompts.py` (401 lines)

**Purpose:** Centralized LLM prompts

**Key Constants:**
```python
IMAGE_PROMPT_ENHANCEMENT_SYSTEM_MESSAGE: Final[str]
IMAGE_PROMPT_ENHANCEMENT_PROMPT: Final[str]
# Plus many other prompts for different features
```

**Exports:**
```python
from src.ai.prompts import (
    IMAGE_PROMPT_ENHANCEMENT_SYSTEM_MESSAGE,
    IMAGE_PROMPT_ENHANCEMENT_PROMPT
)
```

### `src/telegram/handlers/` - Telegram Command Handlers

#### `image_handler.py` (436 lines)

**Purpose:** Handle `/image=` commands

**Key Classes:**
- `ImageHandler(BaseHandler)` - Main handler

**Key Methods:**
```python
async def handle_image_command(message, client, chat_id, sender_info)
async def process_image_command(...)
async def _process_single_request(...)
async def _send_image(...)
def _parse_image_command(message) -> Optional[Dict[str, Any]]
```

**Dependencies:**
- ImageGenerator
- ImageQueue (global instance)
- PromptEnhancer
- Rate limiter
- Error handler
- Metrics

**Exports:**
```python
from src.telegram.handlers.image_handler import ImageHandler
```

### `src/core/` - Core Configuration

#### `config.py` (311 lines)

**Purpose:** Pydantic-based configuration

**Key Classes:**
- `Config(BaseSettings)` - Main config class

**Key Fields:**
```python
flux_worker_url: str
sdxl_worker_url: str
sdxl_api_key: Optional[str]
llm_provider: str
openrouter_api_key: Optional[str]
gemini_api_key: Optional[str]
```

**Key Properties:**
```python
@property
def is_image_generation_enabled(self) -> bool
    
@property
def is_ai_enabled(self) -> bool
```

**Exports:**
```python
from src.core.config import Config, get_settings

config = get_settings()  # Get singleton
```

#### `constants.py` (50 lines)

**Purpose:** Global constants

**Image Generation Constants:**
```python
SUPPORTED_IMAGE_MODELS: Final[list[str]] = ["flux", "sdxl"]
IMAGE_GENERATION_TIMEOUT: Final[int] = 120
IMAGE_GENERATION_CONNECT_TIMEOUT: Final[int] = 30
MAX_IMAGE_PROMPT_LENGTH: Final[int] = 1000
IMAGE_TEMP_DIR: Final[str] = "temp/images"
DEFAULT_FLUX_WORKER_URL: Final[str] = "https://..."
DEFAULT_SDXL_WORKER_URL: Final[str] = "https://..."
```

**Exports:**
```python
from src.core.constants import (
    SUPPORTED_IMAGE_MODELS,
    IMAGE_GENERATION_TIMEOUT,
    MAX_IMAGE_PROMPT_LENGTH
)
```

### `src/utils/` - Utility Functions

#### `error_handler.py` (215 lines)

**Purpose:** Centralized error handling

**Key Classes:**
- `ErrorHandler` - Static methods for errors

**Key Methods:**
```python
@staticmethod
def get_user_message(error: Exception) -> str

@staticmethod
def log_error(error: Exception, context: str) -> None

@staticmethod
def should_retry(error: Exception, attempt: int, max_retries: int) -> bool
```

**Image-Specific Errors:**
- Timeout errors
- Rate limit errors
- Authentication errors
- Network errors
- Content filtering

**Exports:**
```python
from src.utils.error_handler import ErrorHandler
```

#### `validators.py` (262 lines)

**Purpose:** Input validation and sanitization

**Key Classes:**
- `InputValidator` - Static validation methods

**Image-Specific Methods:**
```python
@staticmethod
def validate_image_model(model: str) -> bool

@staticmethod
def validate_image_prompt(prompt: str) -> str
```

**Exports:**
```python
from src.utils.validators import InputValidator
```

#### `retry.py`

**Purpose:** Retry decorator with backoff

**Key Decorators:**
```python
@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
async def function():
    pass
```

**Exports:**
```python
from src.utils.retry import retry_with_backoff
```

## File Responsibilities

### Single Responsibility Principle

Each file has one clear purpose:

| File | Responsibility | Lines | Complexity |
|------|---------------|-------|------------|
| `image_generator.py` | HTTP communication with workers | 259 | Medium |
| `image_queue.py` | Queue state management | 359 | High |
| `prompt_enhancer.py` | LLM prompt enhancement | 99 | Low |
| `image_handler.py` | Telegram command interface | 436 | High |
| `config.py` | Configuration validation | 311 | Medium |
| `constants.py` | Global constants | 50 | Low |
| `error_handler.py` | Error handling logic | 215 | Medium |
| `validators.py` | Input validation | 262 | Medium |

### Separation of Concerns

```
Presentation Layer:
  └─ image_handler.py (Telegram UI)

Business Logic:
  ├─ image_queue.py (Queue management)
  ├─ prompt_enhancer.py (Enhancement logic)
  └─ image_generator.py (Generation logic)

Infrastructure:
  ├─ config.py (Configuration)
  ├─ error_handler.py (Error handling)
  └─ validators.py (Validation)
```

## Import Dependencies

### Dependency Graph

```
image_handler.py
  ├─→ image_generator.py
  ├─→ image_queue.py (global)
  ├─→ prompt_enhancer.py
  ├─→ rate_limiter.py
  ├─→ error_handler.py
  └─→ validators.py

image_generator.py
  ├─→ config.py
  ├─→ constants.py
  ├─→ error_handler.py
  └─→ retry.py

image_queue.py
  ├─→ constants.py
  └─→ logging.py

prompt_enhancer.py
  ├─→ processor.py (AIProcessor)
  ├─→ prompts.py
  └─→ constants.py
```

### No Circular Dependencies

✅ Clean dependency hierarchy  
✅ No circular imports  
✅ Clear separation of layers  

### Example Imports

```python
# image_handler.py
from ...ai.image_generator import ImageGenerator
from ...ai.image_queue import image_queue, ImageStatus
from ...ai.prompt_enhancer import PromptEnhancer
from ...ai.processor import AIProcessor
from ...core.constants import SUPPORTED_IMAGE_MODELS
from ...utils.rate_limiter import get_ai_rate_limiter
from ...utils.error_handler import ErrorHandler
from ...utils.validators import InputValidator
```

## Code Patterns

### Pattern 1: Async/Await Throughout

```python
# All I/O operations are async
async def enhance_prompt(self, prompt: str) -> str:
    enhanced = await self._ai_processor.execute_custom_prompt(...)
    return enhanced

async def generate_with_flux(self, prompt: str) -> Tuple:
    response = await self._make_flux_request(prompt)
    return (True, image_path, None)
```

### Pattern 2: Tuple Return for Results

```python
# Success/failure with optional data
(success: bool, data: Optional[T], error: Optional[str])

# Examples
(True, "/path/to/image.png", None)  # Success
(False, None, "Error message")       # Failure
```

### Pattern 3: Type Hints Everywhere

```python
def add_request(
    self,
    model: str,
    prompt: str,
    user_id: int
) -> str:
    """Add request with full type annotations."""
    pass
```

### Pattern 4: Graceful Fallback

```python
async def enhance_prompt(self, prompt: str) -> str:
    try:
        # Try enhancement
        enhanced = await self._ai_processor.execute_custom_prompt(...)
        return enhanced
    except Exception:
        # Fallback to original
        return prompt  # Never fail completely
```

### Pattern 5: Comprehensive Logging

```python
self._logger.info(f"Added Flux request {request_id}")
self._logger.warning(f"Enhancement failed, using original")
self._logger.error(f"Generation error: {e}", exc_info=True)
```

### Pattern 6: Singleton Pattern

```python
# Global instance
image_queue = ImageQueue()

# Usage
from src.ai.image_queue import image_queue
request_id = image_queue.add_request(...)
```

## Extension Points

### Adding New Image Model

**Files to modify:**

1. `constants.py`:
```python
SUPPORTED_IMAGE_MODELS = ["flux", "sdxl", "newmodel"]
```

2. `config.py`:
```python
newmodel_worker_url: str = Field(...)
newmodel_api_key: Optional[str] = Field(...)
```

3. `image_queue.py`:
```python
self._newmodel_queue: List[ImageRequest] = []
self._newmodel_processing: bool = False
```

4. `image_generator.py`:
```python
async def generate_with_newmodel(self, prompt: str) -> Tuple:
    # Implementation
    pass
```

5. `image_handler.py`:
```python
elif model == "newmodel":
    success, path, error = await self._image_generator.generate_with_newmodel(prompt)
```

See [Adding Models](adding-models.md) for complete guide.

### Adding New Enhancement Strategy

**Files to modify:**

1. `prompts.py`:
```python
NEW_ENHANCEMENT_SYSTEM_MESSAGE = "..."
NEW_ENHANCEMENT_PROMPT = "..."
```

2. `prompt_enhancer.py`:
```python
async def enhance_with_strategy(self, prompt: str, strategy: str) -> str:
    # Implementation
    pass
```

### Adding New Validation

**Files to modify:**

1. `validators.py`:
```python
@staticmethod
def validate_new_thing(value: str) -> bool:
    # Implementation
    return True
```

### Adding New Error Type

**Files to modify:**

1. `error_handler.py`:
```python
if "new_error_pattern" in error_str:
    return "🔴 New error message for users"
```

---

**Next:** [Testing Guide](testing.md) for writing tests
