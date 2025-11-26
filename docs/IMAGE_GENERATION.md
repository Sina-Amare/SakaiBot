# Image Generation Feature Documentation

## Overview

SakaiBot includes robust text-to-image generation functionality supporting both Flux and SDXL models via Cloudflare Workers. The feature includes LLM-based prompt enhancement, queue-based processing, and comprehensive error handling.

## Architecture

### Components

1. **ImageGenerator** (`src/ai/image_generator.py`)
   - Handles HTTP communication with Cloudflare Workers
   - Supports both Flux (GET) and SDXL (POST with Bearer auth)
   - Implements retry logic and error handling
   - Manages temporary image file storage

2. **PromptEnhancer** (`src/ai/prompt_enhancer.py`)
   - Uses existing AIProcessor (OpenRouter/Gemini) to enhance user prompts
   - Specialized system message for image generation prompt engineering
   - Falls back to original prompt if enhancement fails

3. **ImageQueue** (`src/ai/image_queue.py`)
   - Separate FIFO queues for Flux and SDXL
   - Each model processes independently (concurrent processing)
   - Sequential processing within each model queue
   - Status tracking and queue position management

4. **ImageHandler** (`src/telegram/handlers/image_handler.py`)
   - Telegram command handler for `/image` commands
   - Integrates with queue, rate limiting, and metrics
   - Provides status updates and error messages

## Command Format

### Syntax

```
/image=<model>/<prompt>
```

### Models

- **flux**: Flux model via Cloudflare Worker (GET, no auth)
- **sdxl**: SDXL model via Cloudflare Worker (POST, Bearer auth)

### Examples

```
/image=flux=a beautiful sunset over mountains
/image=sdxl=futuristic cyberpunk cityscape at night
/image=flux=cat
/image=sdxl=portrait of a warrior
```

## Prompt Enhancement

User prompts are automatically enhanced using the configured LLM provider (OpenRouter or Gemini) before being sent to the image generation worker.

### Enhancement Process

1. User sends simple prompt: `/image=flux=cat`
2. Prompt is validated and sanitized
3. LLM enhances the prompt: "A beautiful orange tabby cat sitting on a windowsill, soft natural lighting, photorealistic style, detailed fur texture, peaceful atmosphere"
4. Enhanced prompt is used for image generation
5. If enhancement fails, original prompt is used with a warning log

### Enhancement System Message

The system uses a specialized prompt from `src/ai/prompts.py`:
- `IMAGE_PROMPT_ENHANCEMENT_SYSTEM_MESSAGE`
- `IMAGE_PROMPT_ENHANCEMENT_PROMPT`

## Queue Processing

### Separate Queues Per Model

- **Flux Queue**: Processes Flux requests sequentially (FIFO)
- **SDXL Queue**: Processes SDXL requests sequentially (FIFO)
- **Independent Processing**: Flux and SDXL can process simultaneously

### Queue Behavior

1. User sends `/image=flux=prompt1`
2. Request added to Flux queue (position 1)
3. User immediately sends `/image=sdxl=prompt2`
4. Request added to SDXL queue (position 1)
5. Both requests process concurrently (different models)
6. User sends `/image=flux=prompt3`
7. Request added to Flux queue (position 2)
8. Waits for first Flux request to complete

### Status Updates

- "🎨 در حال پردازش درخواست تصویر با {MODEL}..."
- "⏳ در صف {MODEL}: موقعیت {position}..." (if queued)
- "🎨 در حال بهبود prompt با هوش مصنوعی..."
- "🖼️ در حال تولید تصویر با {MODEL}..."
- "📤 در حال ارسال تصویر..."

## Worker API Details

### Flux Worker

- **URL**: `https://image-smoke-ad69.fa-ra9931143.workers.dev/?prompt={prompt}`
- **Method**: GET
- **Authentication**: None
- **Request**: Query parameter `prompt` (URL encoded)
- **Response**: Image (PNG/JPG) with `Content-Type: image/*`
- **Timeout**: 120 seconds

### SDXL Worker

- **URL**: `https://image-api.cpt-n3m0.workers.dev/`
- **Method**: POST
- **Authentication**: `Bearer {SDXL_API_KEY}` header
- **Request Body**: `{"prompt": "..."}`
- **Response**: PNG image with `Content-Type: image/png`
- **Timeout**: 120 seconds
- **Error Responses**:
  - `401`: Unauthorized (invalid/missing API key)
  - `405`: Method not allowed
  - `400`: Bad request (missing/invalid prompt)
  - `500`: Server error (generation failed)

## Error Handling

### Error Types and Messages

| Error | HTTP Code | User Message |
|-------|-----------|--------------|
| Timeout | - | "⏱️ زمان تولید تصویر به پایان رسید" |
| Rate Limit | 429 | "⚠️ محدودیت استفاده - لطفاً صبر کنید" |
| Unauthorized | 401 | "🔐 خطای احراز هویت: کلید API نامعتبر است" |
| Invalid Request | 400 | "❌ درخواست نامعتبر: لطفاً prompt را بررسی کنید" |
| Network Error | - | "🌐 خطا در ارتباط با سرور تصویر" |
| Content Moderation | 400/403 | "🚫 محتوا توسط سیستم فیلتر شد" |
| Service Error | 500 | "🔧 سرویس تولید تصویر در دسترس نیست" |
| Invalid Model | - | "❌ مدل نامعتبر است" |

### Retry Logic

- **Max Retries**: 3 attempts
- **Backoff**: Exponential (1s, 2s, 4s)
- **Retryable Errors**: Network errors, timeouts, 500 errors
- **Non-Retryable**: 400, 401, 405 (client errors)

## Configuration

### Environment Variables

```env
# Cloudflare Image Generation Workers
FLUX_WORKER_URL=https://image-smoke-ad69.fa-ra9931143.workers.dev
SDXL_WORKER_URL=https://image-api.cpt-n3m0.workers.dev
SDXL_API_KEY=your_sdxl_bearer_token_here
```

### Configuration Validation

- Worker URLs must start with `http://` or `https://`
- SDXL API key validated for format (alphanumeric with dashes/underscores, min 10 chars)
- `is_image_generation_enabled` property checks if at least one model is configured

### Constants

Defined in `src/core/constants.py`:
- `SUPPORTED_IMAGE_MODELS = ["flux", "sdxl"]`
- `IMAGE_GENERATION_TIMEOUT = 120` (seconds)
- `IMAGE_GENERATION_CONNECT_TIMEOUT = 30` (seconds)
- `MAX_IMAGE_PROMPT_LENGTH = 1000`
- `IMAGE_TEMP_DIR = "temp/images"`

## File Management

### Temporary Storage

- Images saved to: `temp/images/image_{model}_{request_id}_{timestamp}.png`
- Directory created automatically if it doesn't exist
- Files cleaned up immediately after sending to Telegram
- Maximum file size validation before sending (prevents DoS)

### Cleanup

- Automatic cleanup after successful send
- Manual cleanup on error
- Directory structure preserved for debugging

## Rate Limiting

Image generation commands use the same rate limiter as AI commands:
- **Limit**: 10 requests per 60 seconds per user
- **Scope**: Per-user (by Telegram user ID)
- **Integration**: Reuses `get_ai_rate_limiter()` from `src/utils/rate_limiter.py`

## Metrics

Image generation tracks the following metrics:

- `image_command.requests` - Total requests (tagged by model)
- `image_command.success` - Successful generations (tagged by model)
- `image_command.errors` - Errors (tagged by model and error type)
- `image_command.rate_limited` - Rate limit hits (tagged by model)
- `image_command.enhancement_duration` - Time spent enhancing prompt
- `image_command.generation_duration` - Time spent generating image

## Testing

### Unit Tests

Located in `tests/unit/`:
- `test_image_generator.py` - ImageGenerator tests (mocked HTTP)
- `test_prompt_enhancer.py` - PromptEnhancer tests (mocked AIProcessor)
- `test_image_queue.py` - ImageQueue tests (queue behavior)
- `test_image_handler.py` - ImageHandler tests (mocked Telegram client)

### Integration Tests

Located in `tests/integration/test_image_integration.py`:
- End-to-end tests with real workers (marked as `@pytest.mark.slow`)
- Requires valid worker URLs and SDXL API key in `.env`
- Tests full flow: enhancement → generation → file creation

### Running Tests

```bash
# Run all image generation unit tests
pytest tests/unit/test_image_*.py -v

# Run integration tests (requires real workers)
pytest tests/integration/test_image_integration.py -v -m slow

# Run with coverage
pytest tests/unit/test_image_*.py --cov=src.ai.image_generator --cov=src.ai.prompt_enhancer --cov=src.ai.image_queue --cov=src.telegram.handlers.image_handler
```

## Troubleshooting

### Common Issues

1. **"SDXL API key invalid or missing"**
   - Check `SDXL_API_KEY` in `.env`
   - Verify API key format (alphanumeric with dashes/underscores)
   - Ensure key is not a placeholder value

2. **"Image generation request timed out"**
   - Worker may be slow or overloaded
   - Check network connectivity
   - Try again later

3. **"Rate limit exceeded"**
   - Wait 60 seconds between requests
   - Check rate limit configuration

4. **"Invalid prompt or request format"**
   - Prompt may be too long (>1000 chars)
   - Prompt may contain invalid characters
   - Check prompt validation

5. **"Service error" or "500"**
   - Worker may be down or experiencing issues
   - Check worker status
   - Retry after a few minutes

### Debugging

Enable debug logging:
```env
DEBUG=true
```

Check logs in `logs/` directory for detailed error information.

## Security Considerations

1. **API Keys**: Stored in `.env`, never logged or exposed in error messages
2. **Prompt Sanitization**: Input validated and sanitized before enhancement
3. **File Size Validation**: Images validated before sending (prevents DoS)
4. **Content Moderation**: Worker-level moderation handled gracefully
5. **Rate Limiting**: Per-user rate limiting prevents abuse

## Future Enhancements

Potential improvements:
- Additional models (Stable Diffusion, DALL-E, etc.)
- Prompt templates/presets (`/image=flux=anime=prompt`)
- Image variations (generate multiple versions)
- Image-to-image workflows
- User preferences (remember preferred model)
- Batch generation (multiple images from one prompt)

## References

- Worker Code: See user-provided SDXL worker implementation
- Flux Worker: `https://image-smoke-ad69.fa-ra9931143.workers.dev`
- SDXL Worker: `https://image-api.cpt-n3m0.workers.dev`
- Prompt Enhancement: Uses existing AIProcessor (OpenRouter/Gemini)

