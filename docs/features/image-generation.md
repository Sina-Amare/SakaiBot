# Image Generation Feature

## Overview

The image generation feature allows users to generate images using AI-powered text-to-image models (Flux and SDXL) via Cloudflare Workers. The feature includes automatic prompt enhancement using LLM, separate FIFO queues per model, and comprehensive error handling.

## User Commands

### Command Format

```
/image=flux=<prompt>
/image=sdxl=<prompt>
```

### Examples

```
/image=flux=a beautiful sunset over mountains
/image=sdxl=futuristic cyberpunk cityscape at night
/image=flux=cat
/image=sdxl=portrait of a warrior
```

## Features

### 1. Automatic Prompt Enhancement

User prompts are automatically enhanced using the configured LLM provider (OpenRouter or Gemini) before being sent to the image generation worker.

**Process:**
1. User sends simple prompt: `/image=flux=cat`
2. Prompt is validated and sanitized
3. LLM enhances the prompt: "A beautiful orange tabby cat sitting on a windowsill, soft natural lighting, photorealistic style, detailed fur texture, peaceful atmosphere"
4. Enhanced prompt is used for image generation
5. If enhancement fails, original prompt is used with a warning log

### 2. Separate FIFO Queues Per Model

- **Flux Queue**: Processes Flux requests sequentially (FIFO)
- **SDXL Queue**: Processes SDXL requests sequentially (FIFO)
- **Independent Processing**: Flux and SDXL can process simultaneously

**Example Flow:**
1. User sends `/image=flux=prompt1` → Added to Flux queue (position 1)
2. User immediately sends `/image=sdxl=prompt2` → Added to SDXL queue (position 1)
3. Both requests process concurrently (different models)
4. User sends `/image=flux=prompt3` → Added to Flux queue (position 2)
5. Waits for first Flux request to complete

### 3. Status Updates

Users receive real-time status updates:
- "🎨 Processing image request with {MODEL}..."
- "⏳ In {MODEL} queue: position {N}..."
- "🎨 Enhancing prompt with AI..."
- "🖼️ Generating image with {MODEL}..."
- "📤 Sending image..."

### 4. Enhanced Prompt as Caption

Generated images are sent with the enhanced prompt as the caption, showing users what prompt was actually used for generation.

## Configuration

### Environment Variables

```env
# Cloudflare Image Generation Workers
FLUX_WORKER_URL=https://image-smoke-ad69.fa-ra9931143.workers.dev
SDXL_WORKER_URL=https://image-api.cpt-n3m0.workers.dev
SDXL_API_KEY=your_sdxl_bearer_token_here
```

### Worker Requirements

- **Flux**: GET request, no authentication required
- **SDXL**: POST request, requires Bearer token authentication

## Error Handling

The feature includes comprehensive error handling with user-friendly English messages:

- **Timeout**: "⏱️ Image generation timed out. Please try again."
- **Rate Limit**: "⚠️ Rate limit exceeded - please wait and try again."
- **Authentication**: "🔐 Authentication error: Invalid API key."
- **Invalid Request**: "❌ Invalid request: Please check your prompt."
- **Network Error**: "🌐 Network error connecting to image server. Please try again."
- **Content Filtered**: "🚫 Content was filtered by the system. Please try a different prompt."
- **Service Unavailable**: "🔧 Image generation service unavailable. Please try again later."

## Rate Limiting

Image generation requests are subject to the same rate limiting as other AI features:
- 10 requests per 60 seconds per user
- Rate limit messages are displayed when exceeded

## File Management

- Generated images are saved to `temp/images/` directory
- Files are automatically cleaned up after sending
- File naming format: `image_{model}_{request_id}_{timestamp}.png`

## Limitations

- Maximum prompt length: 1000 characters
- Timeout: 120 seconds for generation, 30 seconds for connection
- Only PNG/JPG image formats supported
- Temporary files stored locally (disk space consideration)

