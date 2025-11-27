# Command Reference

**Last Updated:** 2024-01-15  
**Audience:** End Users  
**Completeness:** All commands documented

## Table of Contents

- [Command Syntax](#command-syntax)
- [Flux Generation](#flux-generation)
- [SDXL Generation](#sdxl-generation)
- [Command Parameters](#command-parameters)
- [Usage Examples](#usage-examples)
- [Response Format](#response-format)
- [Rate Limits](#rate-limits)
- [Error Messages](#error-messages)

## Command Syntax

### Basic Format

```
/image=<model>=<prompt>
```

### Components

| Component | Description | Required | Valid Values |
|-----------|-------------|----------|--------------|
| `/image` | Command prefix | ✅ Yes | Fixed |
| `=` | First separator | ✅ Yes | Fixed |
| `<model>` | AI model name | ✅ Yes | `flux`, `sdxl` |
| `=` | Second separator | ✅ Yes | Fixed |
| `<prompt>` | Image description | ✅ Yes | 1-1000 characters |

### Important Notes

- ⚠️ Use `=` (equals sign) as separator, not `/` (slash)
- ⚠️ Model name is case-insensitive (`flux`, `FLUX`, `Flux` all work)
- ⚠️ No spaces around `=` separators
- ✅ Prompt can contain spaces, emojis, any language

## Flux Generation

### Overview

Flux is a fast image generation model optimized for speed and iteration.

**Characteristics:**
- ⚡ Speed: 5-10 seconds
- 🔓 Authentication: None required
- 🎨 Quality: Good for most purposes
- 💡 Best for: Quick tests, iterations, casual use

### Syntax

```
/image=flux=<prompt>
```

### Examples

#### Simple Prompts

```bash
# Single word (will be enhanced by AI)
/image=flux=cat

# Simple phrase
/image=flux=sunset

# Basic description
/image=flux=mountain landscape
```

#### Descriptive Prompts

```bash
# Detailed scene
/image=flux=a beautiful orange tabby cat sitting on a windowsill

# With style
/image=flux=futuristic cyberpunk cityscape at night with neon lights

# With mood
/image=flux=peaceful forest path in autumn, golden hour lighting
```

#### Complex Prompts

```bash
# Multiple elements
/image=flux=medieval castle on a cliff overlooking the ocean at sunset, dramatic clouds, fantasy art style

# Technical details
/image=flux=portrait of a warrior, detailed armor, dramatic lighting, high contrast, photorealistic

# Abstract concepts
/image=flux=the concept of time flowing like a river, surreal, colorful, abstract art
```

### Flux-Specific Tips

1. ✅ Great for brainstorming and exploring ideas
2. ✅ Use when you need fast results
3. ✅ Perfect for generating multiple variations quickly
4. ✅ No API key needed - always available

## SDXL Generation

### Overview

SDXL is a high-quality image generation model optimized for detail and realism.

**Characteristics:**
- 🎨 Quality: Excellent, professional-grade
- ⏱️ Speed: 10-15 seconds
- 🔐 Authentication: Bearer token required
- 💡 Best for: Final results, high-quality output

### Syntax

```
/image=sdxl=<prompt>
```

### Examples

#### Simple Prompts

```bash
# AI will add detail
/image=sdxl=cat

# Basic scene
/image=sdxl=mountain landscape

# Portrait
/image=sdxl=warrior
```

#### High-Quality Prompts

```bash
# Photorealistic
/image=sdxl=professional portrait photograph of a woman, natural lighting, 50mm lens, shallow depth of field

# Artistic style
/image=sdxl=oil painting of a sunset over the ocean, impressionist style, vibrant colors

# Detailed scene
/image=sdxl=ancient library with towering bookshelves, warm lighting, dust particles in the air, cinematic
```

#### Technical Prompts

```bash
# Photography terms
/image=sdxl=landscape photography, golden hour, wide angle, dramatic sky, long exposure

# Art styles
/image=sdxl=digital art, concept art, fantasy character design, detailed, trending on artstation

# Specific requirements
/image=sdxl=product photography, white background, professional lighting, high resolution, commercial quality
```

### SDXL-Specific Tips

1. ✅ Use for final, publication-ready images
2. ✅ Better at understanding complex prompts
3. ✅ Produces more detailed and realistic results
4. ✅ Worth the extra 5-10 seconds for quality

## Command Parameters

### Model Selection

| Model | Pros | Cons | Use When |
|-------|------|------|----------|
| **flux** | Fast, no auth, always available | Lower detail | Testing, iteration, casual use |
| **sdxl** | High quality, better detail | Slower, needs auth | Final images, professional work |

### Prompt Guidelines

#### Length Limits

- **Minimum:** 1 character (will be enhanced)
- **Maximum:** 1000 characters
- **Recommended:** 10-200 characters (AI enhances shorter prompts)

#### Content Guidelines

✅ **Allowed:**
- Descriptive text in any language
- Style specifications (art style, photography terms)
- Mood and atmosphere descriptions
- Technical details (lighting, camera angles)
- Multiple subjects and elements

❌ **Not Recommended:**
- Violent or harmful content (may be filtered)
- Personal/private information
- Copyrighted character names (may not work well)

### Enhancement Behavior

All prompts are automatically enhanced:

```
Your Input    → AI Enhancement           → Sent to Model
"cat"         → "A beautiful orange..."  → [Image Generated]
```

**What Enhancement Adds:**
- Lighting details (natural light, golden hour)
- Style specifications (photorealistic, detailed)
- Composition guidance (shallow depth of field)
- Atmosphere and mood (peaceful, dramatic)
- Technical quality markers (high quality, detailed)

## Usage Examples

### By Use Case

#### Quick Concepts

```bash
# Fast exploration
/image=flux=robot
/image=flux=dragon
/image=flux=spaceship
```

#### Character Design

```bash
# Flux for iteration
/image=flux=fantasy elf character, green cloak, bow and arrow

# SDXL for final
/image=sdxl=fantasy elf character, detailed costume design, professional concept art
```

#### Landscapes

```bash
# Natural scenes
/image=flux=mountain valley with river
/image=sdxl=mountain valley with river, autumn colors, dramatic lighting, photorealistic

# Urban scenes
/image=flux=modern city skyline at night
/image=sdxl=modern city skyline at night, long exposure, light trails, cinematic
```

#### Product/Commercial

```bash
# Product shots (SDXL recommended)
/image=sdxl=luxury watch on marble surface, professional lighting
/image=sdxl=coffee cup on wooden table, morning light, cozy atmosphere
```

### By Prompt Style

#### Minimal (AI does the work)

```bash
/image=flux=sunset
/image=flux=cat
/image=sdxl=warrior
```

#### Balanced (some guidance)

```bash
/image=flux=sunset over ocean, dramatic colors
/image=flux=orange cat on windowsill
/image=sdxl=armored warrior, medieval, detailed
```

#### Detailed (full control)

```bash
/image=sdxl=breathtaking sunset over calm ocean, vibrant orange and pink sky, silhouette of palm trees, golden hour, photorealistic, high quality

/image=sdxl=professional portrait of an armored medieval warrior, detailed steel armor, dramatic side lighting, shallow depth of field, cinematic, 50mm lens
```

## Response Format

### Success Response

When generation succeeds, you receive:

```
[Image File]

Caption:
🎨 Image generated with FLUX

Enhanced prompt:
A beautiful orange tabby cat sitting on a windowsill,
soft natural lighting, photorealistic style, detailed
fur texture, peaceful atmosphere
```

### Status Updates

During processing:

```
🎨 Processing image request with FLUX...
```
↓
```
⏳ In FLUX queue: position 2...
```
↓
```
🎨 Enhancing prompt with AI...
```
↓
```
🖼️ Generating image with FLUX...
```
↓
```
📤 Sending image...
```

### Queue Position

If others are generating:

```
⏳ In FLUX queue: position 3...
```

This means:
- 2 images ahead of yours
- Estimated wait: ~20-40 seconds
- Position updates every 2 seconds

## Rate Limits

### Current Limits

```
Requests: 10 per 60 seconds (per user)
```

### How It Works

1. Each user has independent rate limit counter
2. Counter resets after 60 seconds
3. Both Flux and SDXL count toward the same limit
4. Failed requests don't count

### Rate Limit Response

```
⚠️ Rate limit exceeded

You have reached the request limit.
Please wait 60 seconds.
Remaining requests: 0
```

### Best Practices

- ✅ Wait for results before sending next request
- ✅ Don't spam commands if first one is processing
- ✅ Use Flux for quick tests to conserve limit
- ⚠️ If you hit limit, wait the full 60 seconds

## Error Messages

### Validation Errors

#### Invalid Command Format

```
❌ Invalid command format.
Usage: /image=flux=<prompt> or /image=sdxl=<prompt>
Example: /image=flux=a beautiful sunset
```

**Cause:** Wrong separator or missing components

**Fix:** Use `=` as separator, not `/` or spaces

#### Invalid Model

```
❌ Invalid model: flx
Supported models: flux, sdxl
```

**Cause:** Typo in model name

**Fix:** Use exactly `flux` or `sdxl`

#### Prompt Too Long

```
❌ Prompt error: Image prompt too long (max 1000 characters, got 1523)
```

**Cause:** Prompt exceeds 1000 characters

**Fix:** Shorten your prompt, let AI enhancement add detail

#### Empty Prompt

```
❌ Prompt error: Image prompt cannot be empty after sanitization
```

**Cause:** Prompt contains only whitespace or special characters

**Fix:** Add descriptive text

### Generation Errors

#### Timeout

```
⏱️ Image generation timed out. Please try again.
```

**Cause:** Worker took too long (>120 seconds)

**Fix:** Try again, use simpler prompt

#### Rate Limit

```
⚠️ Rate limit exceeded - please wait and try again.
```

**Cause:** Too many requests to worker API

**Fix:** Wait 60 seconds, try again

#### Authentication Error (SDXL only)

```
🔐 Authentication error: Invalid API key.
```

**Cause:** SDXL API key invalid or missing

**Fix:** Contact administrator to check configuration

#### Network Error

```
🌐 Network error connecting to image server. Please try again.
```

**Cause:** Cannot reach worker URL

**Fix:** Check internet connection, try again

#### Service Unavailable

```
🔧 Image generation service unavailable. Please try again later.
```

**Cause:** Worker is down or overloaded

**Fix:** Wait a few minutes, try again

#### Content Filtered

```
🚫 Content was filtered by the system. Please try a different prompt.
```

**Cause:** Prompt triggered content moderation

**Fix:** Rephrase prompt, avoid sensitive content

### Other Errors

For unlisted errors, see [Common Issues](../troubleshooting/common-issues.md).

---

**Next:** [Best Practices](best-practices.md) for writing effective prompts
