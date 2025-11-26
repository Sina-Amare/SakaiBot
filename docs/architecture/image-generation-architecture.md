# Image Generation Architecture

## System Overview

The image generation feature is built with a modular architecture that separates concerns into distinct components:

```
User Command → ImageHandler → ImageQueue → PromptEnhancer → ImageGenerator → Cloudflare Worker
```

## Component Architecture

### 1. ImageHandler (`src/telegram/handlers/image_handler.py`)

**Responsibility**: Telegram command handling and user interaction

**Key Functions:**
- Parse `/image=flux=<prompt>` and `/image=sdxl=<prompt>` commands
- Validate model and prompt
- Check rate limits
- Add requests to queue
- Provide status updates to users
- Send generated images to Telegram

**Flow:**
1. `handle_image_command()` - Entry point, validates and queues request
2. `process_image_command()` - Async processing, waits for queue position
3. `_process_single_request()` - Actual generation workflow
4. `_send_image()` - Sends image to Telegram with caption

### 2. ImageQueue (`src/ai/image_queue.py`)

**Responsibility**: Request queue management with separate FIFO queues per model

**Design Decision**: Separate queues for Flux and SDXL
- Allows concurrent processing of different models
- Maintains FIFO order within each model
- Prevents blocking between models

**Key Data Structures:**
```python
_flux_queue: List[ImageRequest]      # FIFO queue for Flux
_sdxl_queue: List[ImageRequest]      # FIFO queue for SDXL
_flux_processing: bool               # Processing flag for Flux
_sdxl_processing: bool                # Processing flag for SDXL
_requests: Dict[str, ImageRequest]    # Request lookup by ID
```

**Key Methods:**
- `add_request()` - Add request to appropriate queue
- `try_start_processing()` - Atomically start processing if next in line
- `get_queue_position()` - Get position in queue
- `mark_completed()` / `mark_failed()` - Update request status

### 3. PromptEnhancer (`src/ai/prompt_enhancer.py`)

**Responsibility**: LLM-based prompt enhancement

**Design Decision**: Mandatory enhancement with fallback
- Always attempts to enhance prompts for better image quality
- Falls back to original prompt if enhancement fails
- Uses existing AIProcessor infrastructure

**Enhancement Process:**
1. Check if AI processor is configured
2. Format enhancement prompt with user input
3. Call AI processor with specialized system message
4. Validate and clean enhanced output
5. Truncate if too long
6. Remove markdown code blocks if present
7. Return enhanced prompt or fallback to original

**Prompts Used:**
- `IMAGE_PROMPT_ENHANCEMENT_SYSTEM_MESSAGE` - System context
- `IMAGE_PROMPT_ENHANCEMENT_PROMPT` - User prompt template

### 4. ImageGenerator (`src/ai/image_generator.py`)

**Responsibility**: HTTP communication with Cloudflare Workers

**Design Decision**: Different authentication per worker
- Flux: GET request, no authentication
- SDXL: POST request, Bearer token authentication

**Key Methods:**
- `generate_with_flux()` - Generate with Flux worker (GET)
- `generate_with_sdxl()` - Generate with SDXL worker (POST)
- `_make_flux_request()` - HTTP GET with query parameters
- `_make_sdxl_request()` - HTTP POST with JSON body and Bearer auth
- `_save_image()` - Save binary response to temp directory

**Error Handling:**
- Retry logic with exponential backoff (3 retries)
- Comprehensive HTTP status code handling
- Timeout handling (120s read, 30s connect)
- Network error handling

**HTTP Client Configuration:**
```python
httpx.AsyncClient(
    timeout=httpx.Timeout(
        connect=30,    # Connection timeout
        read=120,      # Read timeout
        write=120,     # Write timeout
        pool=30        # Pool timeout
    ),
    limits=httpx.Limits(
        max_keepalive_connections=5,
        max_connections=10
    ),
    follow_redirects=True
)
```

## Data Flow

### Request Flow

```
1. User sends: /image=flux=cat
   ↓
2. ImageHandler.parse_image_command()
   → Extracts: model="flux", prompt="cat"
   ↓
3. ImageHandler.handle_image_command()
   → Validates model and prompt
   → Checks rate limit
   → Adds to queue via ImageQueue.add_request()
   ↓
4. ImageHandler.process_image_command()
   → Waits for queue position
   → Calls try_start_processing() when ready
   ↓
5. ImageHandler._process_single_request()
   → PromptEnhancer.enhance_prompt("cat")
   → ImageGenerator.generate_with_flux(enhanced_prompt)
   ↓
6. ImageGenerator._make_flux_request()
   → HTTP GET to Flux worker
   → Receives PNG image bytes
   ↓
7. ImageGenerator._save_image()
   → Saves to temp/images/image_flux_{id}_{timestamp}.png
   ↓
8. ImageHandler._send_image()
   → Sends image to Telegram with enhanced prompt as caption
   → Cleans up temp file
```

### Queue Processing Flow

```
Request 1: /image=flux=prompt1
  → Added to Flux queue [position 1]
  → try_start_processing() returns True
  → Starts processing immediately

Request 2: /image=sdxl=prompt2 (sent immediately after Request 1)
  → Added to SDXL queue [position 1]
  → try_start_processing() returns True
  → Starts processing immediately (different model, no blocking)

Request 3: /image=flux=prompt3 (sent while Request 1 is processing)
  → Added to Flux queue [position 2]
  → try_start_processing() returns False (Request 1 still processing)
  → Waits in loop, checking every 2 seconds
  → When Request 1 completes, try_start_processing() returns True
  → Starts processing
```

## Configuration Integration

### Config Class (`src/core/config.py`)

**New Fields:**
```python
flux_worker_url: Optional[str]
sdxl_worker_url: Optional[str]
sdxl_api_key: Optional[str]

@property
def is_image_generation_enabled(self) -> bool:
    """Check if image generation is properly configured."""
```

**Validation:**
- URL format validation (must start with http:// or https://)
- API key validation (excludes placeholder values)

### Constants (`src/core/constants.py`)

**New Constants:**
```python
SUPPORTED_IMAGE_MODELS: Final[list[str]] = ["flux", "sdxl"]
IMAGE_GENERATION_TIMEOUT: Final[int] = 120  # seconds
IMAGE_GENERATION_CONNECT_TIMEOUT: Final[int] = 30  # seconds
MAX_IMAGE_PROMPT_LENGTH: Final[int] = 1000
IMAGE_TEMP_DIR: Final[str] = "temp/images"
DEFAULT_FLUX_WORKER_URL: Final[str] = "..."
DEFAULT_SDXL_WORKER_URL: Final[str] = "..."
```

## Error Handling Architecture

### Exception Hierarchy

```
AIProcessorError (base)
  ├── ImageGenerationError
  ├── ImageModelError
  ├── ImagePromptError
  ├── ImageWorkerError
  └── ImageQueueError
```

### Error Flow

1. **Validation Errors**: Caught in `handle_image_command()`, sent directly to user
2. **Rate Limit Errors**: Caught in `handle_image_command()`, sent to user
3. **Generation Errors**: Caught in `_process_single_request()`, logged and sent to user
4. **Network Errors**: Caught in `ImageGenerator`, retried with backoff, then reported
5. **Queue Errors**: Caught in `process_image_command()`, logged and reported

### Error Messages

All error messages are in English (UI/UX), while prompts remain in Persian as configured. Error messages are centralized in `ErrorHandler.get_user_message()`.

## Testing Architecture

### Unit Tests

- `test_image_generator.py` - HTTP client mocking, error scenarios
- `test_prompt_enhancer.py` - LLM response mocking, fallback scenarios
- `test_image_queue.py` - Queue logic, concurrent processing
- `test_image_handler.py` - Command parsing, Telegram integration

### Integration Tests

- `test_image_integration.py` - End-to-end flow (requires test workers)

### Test Coverage

- Success scenarios for both models
- Error scenarios (timeout, rate limit, network errors)
- Queue behavior (FIFO, concurrent processing)
- Prompt enhancement (success and fallback)
- Command parsing (valid and invalid formats)

## Security Considerations

1. **API Key Storage**: SDXL API key stored in `.env`, never logged or exposed
2. **Input Validation**: All prompts sanitized and validated
3. **Content Moderation**: Worker responses checked for moderation status codes
4. **Rate Limiting**: Per-user rate limiting prevents abuse
5. **Error Messages**: Never expose internal URLs or API keys

## Performance Considerations

1. **HTTP Client Reuse**: Single httpx.AsyncClient instance per ImageGenerator
2. **Connection Pooling**: Limited to 10 connections, 5 keepalive
3. **Concurrent Processing**: Different models process simultaneously
4. **Temporary Files**: Cleaned up after sending to prevent disk bloat
5. **Queue Efficiency**: O(1) lookup by request ID, O(n) queue position

## Future Extensibility

The architecture supports:
- Additional models (add new queue, new generator method)
- Prompt templates/presets (`/image=flux=anime=prompt`)
- Image variations (img2img workflows)
- Batch generation (multiple variations)
- User preferences (remember preferred model)

