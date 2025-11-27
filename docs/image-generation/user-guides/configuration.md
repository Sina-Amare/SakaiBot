# Configuration Guide

**Last Updated:** 2024-01-15  
**Audience:** Administrators  
**Complexity:** Intermediate

## Table of Contents

- [Prerequisites](#prerequisites)
- [Configuration Files](#configuration-files)
- [Worker Configuration](#worker-configuration)
- [Environment Variables](#environment-variables)
- [Validation](#validation)
- [Testing Configuration](#testing-configuration)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before configuring image generation:

1. ✅ Cloudflare Workers deployed for Flux and/or SDXL
2. ✅ Worker URLs accessible from your SakaiBot instance
3. ✅ SDXL API key (if using SDXL)
4. ✅ LLM provider configured (OpenRouter or Gemini) for prompt enhancement

## Configuration Files

Image generation uses two configuration sources:

### 1. Environment Variables (`.env`)

Primary configuration method (recommended):

```env
# Image Generation - Cloudflare Workers
FLUX_WORKER_URL=https://your-flux-worker.workers.dev
SDXL_WORKER_URL=https://your-sdxl-worker.workers.dev
SDXL_API_KEY=your_sdxl_bearer_token_here
```

### 2. Config.ini (Legacy)

Alternative configuration method:

```ini
[ImageGeneration]
flux_worker_url = https://your-flux-worker.workers.dev
sdxl_worker_url = https://your-sdxl-worker.workers.dev
sdxl_api_key = your_sdxl_bearer_token_here
```

**Recommendation:** Use `.env` for modern deployments.

## Worker Configuration

### Flux Worker

#### Requirements

- **Method:** GET request
- **Authentication:** None required
- **Query Parameter:** `prompt` (URL-encoded)
- **Response:** Image binary (PNG/JPG)

#### Example Request

```http
GET https://your-flux-worker.workers.dev?prompt=a%20beautiful%20cat
```

#### Configuration

```env
FLUX_WORKER_URL=https://your-flux-worker.workers.dev
```

**Validation:**
- ✅ Must start with `http://` or `https://`
- ✅ Must be accessible from SakaiBot server
- ✅ No trailing slash

#### Test Command

```bash
curl "https://your-flux-worker.workers.dev?prompt=test" --output test-flux.png
```

Expected: PNG/JPG image file downloaded

### SDXL Worker

#### Requirements

- **Method:** POST request
- **Authentication:** Bearer token in Authorization header
- **Content-Type:** application/json
- **Request Body:** `{"prompt": "your prompt"}`
- **Response:** Image binary (PNG/JPG)

#### Example Request

```http
POST https://your-sdxl-worker.workers.dev
Authorization: Bearer your_token_here
Content-Type: application/json

{
  "prompt": "a beautiful cat"
}
```

#### Configuration

```env
SDXL_WORKER_URL=https://your-sdxl-worker.workers.dev
SDXL_API_KEY=your_bearer_token_here
```

**Validation:**
- ✅ URL must start with `http://` or `https://`
- ✅ API key must be at least 10 characters
- ✅ Cannot contain placeholder text (e.g., "YOUR_API_KEY")

#### Test Command

```bash
curl -X POST "https://your-sdxl-worker.workers.dev" \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}' \
  --output test-sdxl.png
```

Expected: PNG/JPG image file downloaded

## Environment Variables

### Complete Configuration

```env
# ============================================
# IMAGE GENERATION CONFIGURATION
# ============================================

# Flux Worker (Fast Generation)
# - GET request, no authentication
# - Returns PNG/JPG image binary
FLUX_WORKER_URL=https://image-smoke-ad69.fa-ra9931143.workers.dev

# SDXL Worker (High Quality)
# - POST request with JSON body
# - Requires Bearer token authentication
# - Returns PNG/JPG image binary
SDXL_WORKER_URL=https://image-api.cpt-n3m0.workers.dev
SDXL_API_KEY=your_sdxl_bearer_token_here

# ============================================
# LLM CONFIGURATION (Required for Enhancement)
# ============================================

# Choose provider: openrouter or gemini
LLM_PROVIDER=openrouter

# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free

# OR Gemini Configuration
# GEMINI_API_KEY=your_gemini_key_here
# GEMINI_MODEL=gemini-2.0-flash-exp
```

### Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLUX_WORKER_URL` | Optional* | Default URL | Flux worker endpoint |
| `SDXL_WORKER_URL` | Optional* | Default URL | SDXL worker endpoint |
| `SDXL_API_KEY` | For SDXL | None | Bearer token for SDXL |
| `LLM_PROVIDER` | Yes | openrouter | LLM for enhancement |
| `OPENROUTER_API_KEY` | If OpenRouter | None | OpenRouter API key |
| `GEMINI_API_KEY` | If Gemini | None | Gemini API key |

*At least one worker URL is required for image generation to work.

### Security Considerations

🔒 **API Key Security:**
- Never commit `.env` to version control
- Use strong, unique API keys
- Rotate keys periodically
- Limit key permissions if possible

🔒 **Worker Security:**
- Use HTTPS URLs only
- Validate worker responses
- Monitor for unusual activity
- Set up rate limiting on workers

## Validation

### Automatic Validation

SakaiBot validates configuration on startup:

```python
# Validation checks performed:
1. URL format (http:// or https://)
2. API key format (length, no placeholders)
3. Accessibility (if possible)
```

### Manual Validation

Check configuration status:

```python
from src.core.config import get_settings

config = get_settings()

# Check if image generation is enabled
print(f"Image Generation Enabled: {config.is_image_generation_enabled}")

# Check individual components
print(f"Flux URL: {config.flux_worker_url}")
print(f"SDXL URL: {config.sdxl_worker_url}")
print(f"SDXL API Key: {'***' if config.sdxl_api_key else 'Not set'}")
```

### Configuration Status Check

Run diagnostic script:

```bash
python -c "
from src.core.config import get_settings
config = get_settings()
print(f'Flux: {\"✅\" if config.flux_worker_url else \"❌\"}')
print(f'SDXL: {\"✅\" if config.sdxl_worker_url and config.sdxl_api_key else \"❌\"}')
print(f'LLM: {\"✅\" if config.is_ai_enabled else \"❌\"}')
"
```

Expected output:
```
Flux: ✅
SDXL: ✅
LLM: ✅
```

## Testing Configuration

### Using Verification Script

SakaiBot includes a verification script:

```bash
python scripts/verify_image_generation.py
```

**This script:**
1. Tests Flux worker connection
2. Tests SDXL worker connection
3. Verifies prompt enhancement
4. Generates test images
5. Validates image file format

### Expected Output

```
=== Image Generation Verification ===

Testing Flux Worker...
✅ Flux worker accessible
✅ Image generated successfully
✅ File saved: temp/images/test_flux.png

Testing SDXL Worker...
✅ SDXL worker accessible
✅ Authentication successful
✅ Image generated successfully
✅ File saved: temp/images/test_sdxl.png

Testing Prompt Enhancement...
✅ LLM provider configured
✅ Enhancement working
Original: "test"
Enhanced: "A simple test image, high quality, detailed..."

=== All Tests Passed ===
```

### Manual Testing

#### Test Flux

```bash
# Using curl
curl "https://your-flux-worker.workers.dev?prompt=test" \
  --output test-flux.png

# Check file
file test-flux.png
# Expected: test-flux.png: PNG image data...
```

#### Test SDXL

```bash
# Using curl
curl -X POST "https://your-sdxl-worker.workers.dev" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}' \
  --output test-sdxl.png

# Check file
file test-sdxl.png
# Expected: test-sdxl.png: PNG image data...
```

#### Test End-to-End

Send actual command in Telegram:

```
/image=flux=test
```

Expected:
1. Status updates appear
2. Image received within 30 seconds
3. Caption shows enhanced prompt

## Troubleshooting

### Common Configuration Issues

#### Issue: "Image generation not enabled"

**Symptoms:**
- Commands don't work
- No response to `/image=` commands

**Causes:**
- Worker URLs not configured
- URLs invalid format
- SDXL API key missing (if only using SDXL)

**Solutions:**
1. Check `.env` file exists and has correct values
2. Validate URL format (must start with https://)
3. Restart SakaiBot after configuration changes
4. Run verification script to test

#### Issue: "SDXL Authentication Error"

**Symptoms:**
```
🔐 Authentication error: Invalid API key.
```

**Causes:**
- API key incorrect
- API key expired
- API key has wrong format

**Solutions:**
1. Verify SDXL_API_KEY in `.env`
2. Test key with curl command
3. Check with worker administrator
4. Regenerate API key if needed

#### Issue: "Service Unavailable"

**Symptoms:**
```
🔧 Image generation service unavailable. Please try again later.
```

**Causes:**
- Worker is down
- Network connectivity issue
- Worker URL incorrect

**Solutions:**
1. Test worker URL with curl
2. Check worker status/logs
3. Verify network connectivity
4. Check worker URL for typos

#### Issue: "Prompt Enhancement Fails"

**Symptoms:**
- Original prompts used without enhancement
- Warning in logs: "Enhancement failed"

**Causes:**
- LLM provider not configured
- LLM API key invalid
- LLM service down

**Solutions:**
1. Check LLM configuration (OPENROUTER_API_KEY or GEMINI_API_KEY)
2. Verify LLM_PROVIDER setting
3. Test LLM with other features
4. Check LLM service status

### Configuration Validation Checklist

Before deploying:

- [ ] `.env` file created with all required variables
- [ ] Worker URLs use HTTPS protocol
- [ ] No placeholder text in configuration
- [ ] SDXL API key is at least 10 characters
- [ ] LLM provider configured for enhancement
- [ ] Verification script passes all tests
- [ ] Manual curl tests successful
- [ ] End-to-end Telegram test successful
- [ ] `.env` added to `.gitignore`
- [ ] Configuration documented for team

### Getting Help

If configuration issues persist:

1. **Check Logs:**
   ```bash
   tail -f logs/sakaibot.log | grep -i image
   ```

2. **Run Diagnostics:**
   ```bash
   python scripts/verify_image_generation.py
   ```

3. **Review Documentation:**
   - [Common Issues](../troubleshooting/common-issues.md)
   - [Debugging Guide](../troubleshooting/debugging.md)

4. **Contact Support:**
   - Check GitHub issues
   - Consult with team lead
   - Review worker documentation

---

**Next:** [Best Practices](best-practices.md) for optimal configuration
