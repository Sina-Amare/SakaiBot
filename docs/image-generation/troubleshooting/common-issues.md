# Common Issues and Solutions

**Last Updated:** 2024-01-15  
**Audience:** Users, Administrators, Developers  
**Purpose:** Quick troubleshooting reference

## Table of Contents

- [User Issues](#user-issues)
- [Configuration Issues](#configuration-issues)
- [Network Issues](#network-issues)
- [Performance Issues](#performance-issues)
- [Error Messages Reference](#error-messages-reference)

## User Issues

### Issue: Command Not Recognized

**Symptoms:**
```
User sends: /image=flux=cat
Bot: No response or "Command not found"
```

**Possible Causes:**
1. Image generation not enabled
2. Wrong command format
3. Bot not running

**Solutions:**

**Check 1: Verify Command Format**
```bash
# Correct format (use = not /)
/image=flux=cat       ✓
/image=sdxl=dog       ✓

# Wrong formats
/image flux cat       ✗
/image/flux/cat       ✗
/image-flux-cat       ✗
```

**Check 2: Verify Feature Enabled**
```python
from src.core.config import get_settings
config = get_settings()
print(config.is_image_generation_enabled)
# Should print: True
```

**Check 3: Check Bot Status**
```bash
# Check if process running
ps aux | grep sakaibot

# Check logs
tail -f logs/sakaibot.log
```

### Issue: Rate Limit Exceeded

**Symptoms:**
```
⚠️ Rate limit exceeded
You have reached the request limit.
Please wait 60 seconds.
Remaining requests: 0
```

**Cause:** User sent more than 10 requests in 60 seconds

**Solutions:**

**Option 1: Wait**
- Wait full 60 seconds
- Counter resets automatically
- Try again

**Option 2: Check Usage**
```python
from src.utils.rate_limiter import get_ai_rate_limiter
limiter = get_ai_rate_limiter()

# Check remaining for user
remaining = await limiter.get_remaining_requests(user_id)
print(f"Remaining: {remaining}/10")
```

**Option 3: Adjust Limits (Admin)**
```python
# In rate_limiter.py
DEFAULT_MAX_REQUESTS = 10  # Increase if needed
DEFAULT_WINDOW_SECONDS = 60
```

### Issue: Long Wait Times

**Symptoms:**
```
⏳ In FLUX queue: position 5...
(Waiting several minutes)
```

**Cause:** Multiple users generating images

**Understanding:**
- Each model processes one request at a time
- Position 5 = 4 requests ahead
- Each request takes ~15-25 seconds
- Expected wait: 60-100 seconds

**Solutions:**

**Option 1: Use Different Model**
```bash
# If Flux queue is long, try SDXL
/image=sdxl=your prompt

# Queues are separate, might be shorter
```

**Option 2: Be Patient**
- Queue position updates every 2 seconds
- Processing is FIFO (fair)
- Your turn will come

**Option 3: Optimize (Developer)**
- See [Performance Tuning](performance.md)
- Consider horizontal scaling
- Optimize worker response time

### Issue: Poor Image Quality

**Symptoms:**
- Image doesn't match expectations
- Low detail or wrong style
- Generic results

**Cause:** Prompt needs improvement

**Solutions:**

**Option 1: Write Better Prompts**
```bash
# Instead of:
/image=flux=cat

# Try:
/image=flux=orange tabby cat sitting on windowsill, natural lighting

# Or:
/image=sdxl=professional portrait of a cat, detailed fur, soft focus background
```

**Option 2: Use SDXL for Quality**
```bash
# Flux: Fast but lower quality
/image=flux=landscape

# SDXL: Slower but higher quality
/image=sdxl=landscape
```

**Option 3: Learn from Enhancements**
- Read the enhanced prompt in image caption
- See what details AI added
- Incorporate in future prompts

**See:** [Best Practices](../user-guides/best-practices.md) for prompt writing tips

### Issue: Content Filtered

**Symptoms:**
```
🚫 Content was filtered by the system.
Please try a different prompt.
```

**Cause:** Prompt triggered content moderation

**Solutions:**

**Option 1: Rephrase Prompt**
```bash
# Avoid explicit content
# Avoid violence/gore
# Use neutral descriptions
```

**Option 2: Check Prompt**
- Remove sensitive keywords
- Use artistic terms instead
- Focus on style, not content

**Example:**
```bash
# Instead of: violent scene
# Try: dramatic action scene

# Instead of: explicit content  
# Try: artistic figure study
```

## Configuration Issues

### Issue: SDXL Authentication Error

**Symptoms:**
```
🔐 Authentication error: Invalid API key.
```

**Cause:** SDXL_API_KEY incorrect or missing

**Solutions:**

**Step 1: Check Configuration**
```bash
# Check .env file
cat .env | grep SDXL_API_KEY

# Should show:
SDXL_API_KEY=your_bearer_token_here
```

**Step 2: Verify Key Format**
```env
# Correct format
SDXL_API_KEY=sk-proj-abcd1234...

# Wrong formats
SDXL_API_KEY="sk-proj-..."  # No quotes
SDXL_API_KEY=YOUR_API_KEY   # Placeholder
SDXL_API_KEY=                # Empty
```

**Step 3: Test Key**
```bash
curl -X POST "https://your-sdxl-worker.workers.dev" \
  -H "Authorization: Bearer YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}' \
  --output test.png

# Should download image
file test.png
# Expected: PNG image data
```

**Step 4: Regenerate Key**
- Contact worker administrator
- Get new API key
- Update .env file
- Restart SakaiBot

### Issue: Worker URL Not Found

**Symptoms:**
```
🌐 Network error connecting to image server.
Please try again.
```

**Cause:** Worker URL incorrect or unreachable

**Solutions:**

**Step 1: Verify URL**
```bash
# Check configuration
python -c "
from src.core.config import get_settings
config = get_settings()
print(f'Flux: {config.flux_worker_url}')
print(f'SDXL: {config.sdxl_worker_url}')
"
```

**Step 2: Test Connectivity**
```bash
# Test Flux
curl "https://your-flux-worker.workers.dev?prompt=test" \
  --output test-flux.png

# Test SDXL
curl -X POST "https://your-sdxl-worker.workers.dev" \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}' \
  --output test-sdxl.png
```

**Step 3: Check URL Format**
```env
# Correct formats
FLUX_WORKER_URL=https://image-smoke-ad69.fa-ra9931143.workers.dev
SDXL_WORKER_URL=https://image-api.cpt-n3m0.workers.dev

# Wrong formats
FLUX_WORKER_URL=http://...      # Use HTTPS
FLUX_WORKER_URL=.../path        # No path needed
FLUX_WORKER_URL=...workers.dev/ # No trailing slash
```

**Step 4: Network Debugging**
```bash
# Check DNS resolution
nslookup image-smoke-ad69.fa-ra9931143.workers.dev

# Check connectivity
ping image-smoke-ad69.fa-ra9931143.workers.dev

# Check firewall
# Ensure outbound HTTPS (443) allowed
```

### Issue: Prompt Enhancement Not Working

**Symptoms:**
- Original prompt used without enhancement
- Warning in logs: "Enhancement failed, using original"

**Cause:** LLM provider not configured

**Solutions:**

**Step 1: Check LLM Configuration**
```bash
python -c "
from src.core.config import get_settings
config = get_settings()
print(f'LLM Enabled: {config.is_ai_enabled}')
print(f'Provider: {config.llm_provider}')
"
```

**Step 2: Verify API Keys**
```env
# For OpenRouter
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free

# For Gemini
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash-exp
```

**Step 3: Test LLM**
```python
from src.ai.processor import AIProcessor

processor = AIProcessor()
result = await processor.execute_custom_prompt(
    user_prompt="test",
    system_message="You are a test assistant."
)
print(result)
# Should get response
```

**Step 4: Check Logs**
```bash
grep -i "enhancement" logs/sakaibot.log
# Look for error messages
```

## Network Issues

### Issue: Timeout Errors

**Symptoms:**
```
⏱️ Image generation timed out. Please try again.
```

**Cause:** Worker took too long (>120 seconds)

**Solutions:**

**Option 1: Retry**
- Automatic retry (3 attempts)
- Manual retry if persists
- Worker might be overloaded

**Option 2: Check Worker Status**
```bash
# Check if worker is responsive
curl -I https://your-worker.workers.dev
# Should return 200 OK quickly
```

**Option 3: Simplify Prompt**
```bash
# Complex prompts take longer
# Try simpler version first
/image=flux=cat
# Instead of long detailed prompt
```

**Option 4: Adjust Timeouts (Developer)**
```python
# In constants.py
IMAGE_GENERATION_TIMEOUT = 120  # Increase if needed
IMAGE_GENERATION_CONNECT_TIMEOUT = 30
```

### Issue: Connection Errors

**Symptoms:**
```
🌐 Network error connecting to image server.
Connection refused / Connection timeout
```

**Possible Causes:**
1. Worker is down
2. Network connectivity issue
3. Firewall blocking
4. DNS resolution failure

**Solutions:**

**Check 1: Worker Status**
```bash
# Test worker directly
curl https://your-worker.workers.dev

# Check Cloudflare status
# Visit status.cloudflare.com
```

**Check 2: Network Connectivity**
```bash
# Test DNS
nslookup your-worker.workers.dev

# Test connectivity
telnet your-worker.workers.dev 443

# Test HTTPS
curl -v https://your-worker.workers.dev
```

**Check 3: Firewall/Proxy**
```bash
# If behind corporate firewall
# Ensure outbound HTTPS allowed
# Check proxy settings

export HTTPS_PROXY=http://proxy:8080
```

**Check 4: Retry Logic**
- System automatically retries (3x)
- Uses exponential backoff
- If all retries fail → user error

## Performance Issues

### Issue: Slow Response Times

**Symptoms:**
- Images take longer than 30 seconds
- Queue moves slowly
- Users complaining about wait

**Diagnosis:**

**Check 1: Measure Times**
```bash
# Check logs for timing
grep "duration" logs/sakaibot.log

# Expected breakdown:
# Enhancement: 3-5s
# Generation: 5-15s (Flux), 10-15s (SDXL)
# Upload: 1-2s
# Total: 10-25s typical
```

**Check 2: Identify Bottleneck**
```python
# Enhancement slow → LLM issue
# Generation slow → Worker issue
# Upload slow → Network issue
```

**Solutions:**

**For Slow Enhancement:**
```python
# Switch LLM provider
LLM_PROVIDER=gemini  # Faster
# Instead of: LLM_PROVIDER=openrouter

# Use faster model
GEMINI_MODEL=gemini-2.0-flash-exp  # Fast
# Instead of: gemini-pro
```

**For Slow Generation:**
- Contact worker administrator
- Worker might be overloaded
- Consider alternative workers
- Use Flux instead of SDXL for speed

**For Slow Upload:**
- Check network bandwidth
- Telegram API rate limits
- Compress images (worker config)

### Issue: High Memory Usage

**Symptoms:**
- Server running out of memory
- Process killed by OOM
- Slow performance

**Diagnosis:**
```bash
# Check memory usage
ps aux | grep sakaibot

# Expected: ~200-500MB
# High: >1GB
```

**Causes:**
1. Temp files not cleaned up
2. Too many concurrent requests
3. Memory leak

**Solutions:**

**Solution 1: Clean Temp Files**
```bash
# Manual cleanup
rm -rf temp/images/*

# Automatic cleanup in code
# Already implemented in _send_image()
```

**Solution 2: Limit Concurrency**
```python
# In queue: Already limited to 1 per model
# If needed, add global limit

MAX_CONCURRENT_GENERATIONS = 2  # Flux + SDXL
```

**Solution 3: Restart Periodically**
```bash
# Cron job to restart daily
0 3 * * * systemctl restart sakaibot
```

## Error Messages Reference

### Complete Error List

| Error Message | Cause | Solution |
|--------------|-------|----------|
| ⏱️ Image generation timed out | Worker timeout | Retry, simplify prompt |
| ⚠️ Rate limit exceeded | Too many requests | Wait 60 seconds |
| 🔐 Authentication error | Invalid API key | Check SDXL_API_KEY |
| ❌ Invalid request | Bad prompt/format | Check prompt format |
| 🌐 Network error | Connection failed | Check network, worker |
| 🚫 Content filtered | Inappropriate prompt | Rephrase prompt |
| 🔧 Service unavailable | Worker down | Wait, try again later |
| ❌ Invalid model | Wrong model name | Use 'flux' or 'sdxl' |
| ❌ Prompt too long | >1000 characters | Shorten prompt |

### Error Codes (HTTP)

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | - |
| 400 | Bad request | Check prompt |
| 401 | Unauthorized | Check API key |
| 405 | Method not allowed | Check worker config |
| 429 | Rate limited | Wait and retry |
| 500 | Server error | Retry later |
| 503 | Service unavailable | Retry later |

### Debug Mode

**Enable detailed logging:**
```python
# In code
import logging
logging.basicConfig(level=logging.DEBUG)

# Check logs
tail -f logs/sakaibot.log
```

**Key log messages:**
```
INFO: Added Flux request img_abc123 to queue
INFO: Started processing Flux request img_abc123
INFO: Request img_abc123 completed
ERROR: Request img_abc123 failed: [error message]
WARNING: Enhancement failed, using original prompt
```

---

**Need more help?** → [Debugging Guide](debugging.md)
