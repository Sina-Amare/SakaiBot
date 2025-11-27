# Getting Started with Image Generation

**Last Updated:** 2024-01-15  
**Difficulty:** Beginner  
**Time to Complete:** 5 minutes

## Table of Contents

- [What is Image Generation?](#what-is-image-generation)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Your First Image](#your-first-image)
- [Understanding Results](#understanding-results)
- [Next Steps](#next-steps)

## What is Image Generation?

SakaiBot's image generation feature allows you to create images from text descriptions using state-of-the-art AI models:

- **Flux**: Fast generation (~5-10 seconds), great for quick iterations
- **SDXL**: High-quality generation (~10-15 seconds), best for final results

### Key Features

✨ **Automatic Enhancement:** Your simple prompts are automatically improved by AI  
⚡ **Fast Processing:** Separate queues ensure minimal wait times  
📊 **Real-time Updates:** See your queue position and generation status  
🎨 **Quality Results:** Both models produce professional-grade images  

## Prerequisites

Before you start:

1. ✅ SakaiBot must be configured with worker URLs (admin task)
2. ✅ You must be authorized to use AI features
3. ✅ Rate limits apply: 10 requests per 60 seconds

> **For Administrators:** See [Configuration Guide](configuration.md) for setup instructions.

## Quick Start

### Basic Command Format

```
/image=<model>=<your prompt>
```

- `<model>`: Either `flux` or `sdxl`
- `<your prompt>`: Your image description (any language)

### Example Commands

```bash
# Simple prompt with Flux (fastest)
/image=flux=cat

# Detailed prompt with SDXL (best quality)
/image=sdxl=a beautiful sunset over mountains

# Complex scene
/image=flux=futuristic cyberpunk cityscape at night with neon lights
```

## Your First Image

Let's generate your first image step by step:

### Step 1: Send the Command

Type in Telegram:
```
/image=flux=sunset
```

### Step 2: Wait for Processing

You'll see status updates:
```
🎨 Processing image request with FLUX...
🎨 Enhancing prompt with AI...
🖼️ Generating image with FLUX...
📤 Sending image...
```

### Step 3: Receive Your Image

- Image is sent with the enhanced prompt as caption
- Original simple prompt: "sunset"
- Enhanced version: "A breathtaking sunset over a calm ocean, vibrant orange and pink hues..."

### Expected Timeline

| Step | Duration | What's Happening |
|------|----------|------------------|
| Validation | Instant | Checking command and rate limits |
| Queue | 0-30s | Waiting for your turn (if others are generating) |
| Enhancement | 3-5s | AI improves your prompt |
| Generation | 5-15s | Creating the image |
| Sending | 1-2s | Uploading to Telegram |
| **Total** | **~10-55s** | Average: 15-25 seconds |

## Understanding Results

### Image Caption

Every generated image includes a caption showing:
```
🎨 Image generated with FLUX

Enhanced prompt:
[The detailed prompt that was actually used]
```

**Why this matters:**
- You can see how AI interpreted your request
- Learn to write better prompts by seeing what works
- Reuse successful enhanced prompts directly

### Queue Position Updates

If others are generating images, you'll see:
```
⏳ In FLUX queue: position 2...
```

This means:
- 1 image is currently generating
- Your image will start after that
- Each position typically takes 10-20 seconds

## Next Steps

Now that you've generated your first image:

### Learn More

- **[Command Reference](command-reference.md)** - All commands and options
- **[Best Practices](best-practices.md)** - Write better prompts
- **[Common Issues](../troubleshooting/common-issues.md)** - Troubleshoot problems

### Try Different Models

```bash
# Fast iteration with Flux
/image=flux=portrait of a warrior

# High quality with SDXL
/image=sdxl=portrait of a warrior
```

**Tip:** Start with Flux for experimenting, use SDXL for final results.

### Experiment with Prompts

```bash
# Minimal (AI will enhance)
/image=flux=cat

# Descriptive (more control)
/image=flux=orange tabby cat sitting on a windowsill

# Style-specific
/image=sdxl=cat, digital art, vibrant colors, detailed
```

### Understand Models

| Feature | Flux | SDXL |
|---------|------|------|
| Speed | ⚡⚡⚡ Fast | ⚡⚡ Moderate |
| Quality | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Excellent |
| Best For | Quick tests, iterations | Final images, prints |
| Auth Required | No | Yes (Bearer token) |

## Common Questions

**Q: How long does it take?**  
A: 10-25 seconds on average, up to 60 seconds if queue is busy.

**Q: Can I generate multiple images at once?**  
A: Yes, but they queue sequentially per model. Flux and SDXL process in parallel.

**Q: What if I get an error?**  
A: See [Common Issues](../troubleshooting/common-issues.md) for solutions.

**Q: Is there a cost?**  
A: Depends on your SakaiBot configuration. Check with your administrator.

**Q: Can I use Persian prompts?**  
A: Yes! Prompts work in any language.

## Tips for Success

1. ✅ **Start simple:** Let AI enhancement do the work
2. ✅ **Use descriptive words:** "beautiful," "detailed," "atmospheric"
3. ✅ **Be patient:** Quality takes time, don't spam requests
4. ✅ **Try both models:** Each has strengths
5. ✅ **Learn from captions:** See what prompts work well

---

**Ready to create amazing images?** Start with simple prompts and let the AI guide you!

**Next:** [Command Reference](command-reference.md) for complete command documentation
