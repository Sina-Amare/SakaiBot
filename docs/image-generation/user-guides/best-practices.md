# Best Practices for Image Generation

**Last Updated:** 2024-01-15  
**Audience:** All Users  
**Level:** Beginner to Advanced

## Table of Contents

- [Writing Effective Prompts](#writing-effective-prompts)
- [Model Selection Strategy](#model-selection-strategy)
- [Optimization Tips](#optimization-tips)
- [Common Mistakes](#common-mistakes)
- [Advanced Techniques](#advanced-techniques)
- [Workflow Recommendations](#workflow-recommendations)

## Writing Effective Prompts

### The Prompt Enhancement System

SakaiBot automatically enhances your prompts using AI. Understanding how this works helps you write better inputs.

**How It Works:**

```
Your Input → AI Analysis → Enhanced Prompt → Image Generation
"cat"      → Add details  → "A beautiful orange..." → [Image]
```

**Key Principle:** Start simple, let AI add complexity.

### Prompt Structure Levels

#### Level 1: Minimal (Let AI Do Everything)

**When to use:** Quick concepts, exploration, casual use

```bash
/image=flux=cat
/image=flux=sunset
/image=flux=castle
```

**Pros:**
- ✅ Fastest to type
- ✅ AI adds professional details
- ✅ Great for brainstorming

**Cons:**
- ⚠️ Less control over specific details
- ⚠️ May not match exact vision

#### Level 2: Guided (Balanced Control)

**When to use:** When you have a clear concept but want AI assistance

```bash
/image=flux=orange cat on windowsill
/image=flux=sunset over ocean with palm trees
/image=sdxl=medieval castle on cliff
```

**Pros:**
- ✅ More control over composition
- ✅ Still benefits from AI enhancement
- ✅ Better results for specific scenes

**Cons:**
- ⚠️ Takes more thought
- ⚠️ May conflict with AI enhancements

#### Level 3: Detailed (Maximum Control)

**When to use:** Professional work, specific requirements, final output

```bash
/image=sdxl=professional portrait photograph of a woman with red hair, natural window lighting, 50mm lens, shallow depth of field, warm color grading, magazine quality

/image=sdxl=fantasy landscape, towering mountains, misty valleys, ancient ruins, golden hour lighting, epic scale, cinematic composition, trending on artstation
```

**Pros:**
- ✅ Maximum control
- ✅ Consistent style
- ✅ Professional results

**Cons:**
- ⚠️ Longer prompts
- ⚠️ Need to understand terminology
- ⚠️ May limit AI creativity

### Essential Prompt Elements

#### 1. Subject (Required)

The main focus of your image.

```bash
# Clear subject
/image=flux=warrior
/image=flux=mountain landscape
/image=flux=coffee cup
```

#### 2. Details (Optional but Recommended)

Specific characteristics of the subject.

```bash
# With details
/image=flux=armored warrior with sword
/image=flux=snow-covered mountain landscape
/image=flux=steaming coffee cup on wooden table
```

#### 3. Style (Optional)

Artistic or photographic style.

```bash
# With style
/image=sdxl=warrior, digital art, fantasy style
/image=sdxl=mountain landscape, oil painting
/image=sdxl=coffee cup, product photography
```

#### 4. Lighting (Optional)

Light quality and direction.

```bash
# With lighting
/image=sdxl=warrior, dramatic side lighting
/image=sdxl=mountain, golden hour, soft light
/image=sdxl=coffee cup, natural morning light
```

#### 5. Mood/Atmosphere (Optional)

Emotional tone of the image.

```bash
# With mood
/image=sdxl=warrior, epic and heroic
/image=sdxl=mountain, peaceful and serene
/image=sdxl=coffee cup, cozy and warm
```

### Power Words for Better Results

#### Quality Modifiers

Use these to improve overall quality:

```
detailed, high quality, professional, realistic, photorealistic,
sharp, clear, crisp, vivid, vibrant, stunning, beautiful
```

**Example:**
```bash
/image=sdxl=cat, detailed, photorealistic, high quality
```

#### Style Keywords

Common styles that work well:

```
photorealistic, digital art, oil painting, watercolor, sketch,
concept art, illustration, fantasy art, sci-fi, cyberpunk,
minimalist, abstract, surreal, impressionist
```

**Example:**
```bash
/image=flux=landscape, digital art, concept art style
```

#### Lighting Terms

Professional lighting descriptions:

```
natural light, golden hour, soft light, dramatic lighting,
rim lighting, backlit, studio lighting, ambient light,
cinematic lighting, moody lighting, bright, dark
```

**Example:**
```bash
/image=sdxl=portrait, natural window light, soft and warm
```

#### Composition Terms

Guide image composition:

```
centered, symmetrical, rule of thirds, wide angle, close-up,
macro, bird's eye view, low angle, Dutch angle, panoramic
```

**Example:**
```bash
/image=sdxl=building, low angle shot, dramatic perspective
```

#### Technical Photography Terms

For photorealistic results:

```
50mm lens, 85mm lens, wide angle, telephoto, shallow depth of field,
bokeh, long exposure, HDR, RAW, professional photography
```

**Example:**
```bash
/image=sdxl=portrait, 85mm lens, shallow depth of field, bokeh
```

## Model Selection Strategy

### Decision Matrix

| Scenario | Recommended Model | Reason |
|----------|-------------------|---------|
| Quick concept testing | Flux | Speed, no auth needed |
| Multiple iterations | Flux | Fast feedback loop |
| Final production image | SDXL | Highest quality |
| Photorealistic portraits | SDXL | Better detail/realism |
| Abstract/artistic | Either | Both handle well |
| Landscape photography | SDXL | Better lighting/detail |
| Simple illustrations | Flux | Good quality, faster |
| Commercial/professional | SDXL | Publication quality |

### Workflow Strategy

**Recommended Approach:**

```
1. Start with Flux (exploration)
   ↓
2. Iterate with Flux (refinement)
   ↓
3. Final with SDXL (production)
```

**Example Workflow:**

```bash
# Step 1: Quick concept
/image=flux=warrior character

# Step 2: Add details and test
/image=flux=armored warrior, fantasy style

# Step 3: Refine further
/image=flux=armored warrior, medieval armor, sword

# Step 4: Final high-quality version
/image=sdxl=medieval armored warrior with ornate armor, holding sword, dramatic lighting, fantasy concept art, detailed, high quality
```

## Optimization Tips

### Speed Optimization

**Goal:** Get results faster

1. **Use Flux for iteration**
   - 5-10 seconds vs 10-15 for SDXL
   - Perfect for testing ideas

2. **Keep prompts concise initially**
   - Let AI enhancement add details
   - Faster to type and send

3. **Avoid queue congestion**
   - Wait for current image before sending next
   - Check queue position before multiple requests

4. **Batch similar requests**
   - Do all Flux tests, then all SDXL finals
   - Minimizes context switching

### Quality Optimization

**Goal:** Get best possible results

1. **Use SDXL for finals**
   - Worth the extra 5-10 seconds
   - Significantly better detail

2. **Write detailed prompts**
   - Specify lighting, style, composition
   - Use technical terms when appropriate

3. **Include quality keywords**
   - "detailed", "high quality", "professional"
   - "photorealistic" for realistic images

4. **Learn from enhancements**
   - Read the enhanced prompt in captions
   - Incorporate successful patterns

### Cost Optimization

**Goal:** Minimize resource usage (if applicable)

1. **Test with Flux first**
   - Cheaper/free (no auth required)
   - Reserve SDXL for confirmed concepts

2. **Respect rate limits**
   - 10 requests per 60 seconds
   - Plan your requests accordingly

3. **Be specific upfront**
   - Avoid iterations due to miscommunication
   - Clear prompts = fewer retries

## Common Mistakes

### ❌ Mistake 1: Overly Complex Initial Prompts

**Wrong:**
```bash
/image=flux=highly detailed photorealistic portrait of a medieval warrior with ornate golden armor featuring intricate engravings and battle damage, holding a legendary sword with glowing runes, standing on a misty battlefield at dawn with dramatic volumetric lighting rays piercing through storm clouds, cinematic composition...
```

**Right:**
```bash
# Start simple
/image=flux=medieval warrior

# Then refine based on result
/image=flux=armored warrior on battlefield, dramatic lighting
```

**Why:** AI enhancement adds much of this detail. Start simple and iterate.

### ❌ Mistake 2: Wrong Model for Use Case

**Wrong:**
```bash
# Using SDXL for quick tests
/image=sdxl=test
/image=sdxl=another test
/image=sdxl=one more test
```

**Right:**
```bash
# Use Flux for iteration
/image=flux=concept 1
/image=flux=concept 2
/image=flux=concept 3

# SDXL for final
/image=sdxl=chosen concept, detailed, high quality
```

**Why:** SDXL is slower. Reserve it for final outputs.

### ❌ Mistake 3: Ignoring Enhancement Results

**Wrong:**
```bash
# Sending same prompt repeatedly
/image=flux=cat
# (receives enhanced: "beautiful orange tabby cat...")
/image=flux=cat
# (same enhancement)
```

**Right:**
```bash
# Learn from enhancement
/image=flux=cat
# (sees enhancement)
# Next time, incorporate insights:
/image=flux=white persian cat, blue eyes
```

**Why:** Enhanced prompts teach you what works. Learn and adapt.

### ❌ Mistake 4: Not Being Specific Enough

**Wrong:**
```bash
/image=sdxl=good picture
/image=sdxl=nice image
/image=sdxl=cool
```

**Right:**
```bash
/image=sdxl=landscape photograph
/image=sdxl=portrait of a person
/image=sdxl=abstract digital art
```

**Why:** Even with AI enhancement, clear subjects produce better results.

### ❌ Mistake 5: Spamming Commands

**Wrong:**
```bash
/image=flux=cat
/image=flux=cat
/image=flux=cat
# (all sent within 2 seconds)
```

**Right:**
```bash
/image=flux=cat
# Wait for result (15-25 seconds)
# Review image
# Then send next request if needed
```

**Why:** Requests queue sequentially. Spamming doesn't speed things up.

### ❌ Mistake 6: Inappropriate Content Expectations

**Wrong:**
```bash
/image=flux=violent scene with blood
/image=flux=explicit content
```

**Right:**
```bash
/image=flux=dramatic action scene
/image=flux=artistic figure study
```

**Why:** Content filters may block inappropriate requests.

## Advanced Techniques

### Technique 1: Style Mixing

Combine multiple style references:

```bash
/image=sdxl=landscape, impressionist painting meets cyberpunk aesthetics

/image=sdxl=portrait, renaissance painting style with modern fashion
```

### Technique 2: Negative Space

Use composition terms to create breathing room:

```bash
/image=sdxl=solitary tree in vast empty field, minimalist composition

/image=sdxl=single subject centered, lots of negative space
```

### Technique 3: Mood Keywords

Strong mood descriptors:

```bash
/image=sdxl=abandoned house, eerie and unsettling atmosphere

/image=sdxl=mountain peak, triumphant and inspiring mood

/image=sdxl=cafe scene, cozy and intimate feeling
```

### Technique 4: Camera Simulation

Simulate specific camera setups:

```bash
/image=sdxl=street photography, 35mm film, grainy, high contrast

/image=sdxl=portrait, medium format camera, 80mm lens, film aesthetic

/image=sdxl=landscape, large format camera, incredible detail, sharp
```

### Technique 5: Lighting Scenarios

Specific lighting setups:

```bash
/image=sdxl=portrait, Rembrandt lighting, dramatic chiaroscuro

/image=sdxl=product, three-point lighting, studio setup

/image=sdxl=scene, practical lights only, cinematic
```

### Technique 6: Temporal Elements

Add time-based context:

```bash
/image=sdxl=city street, early morning fog, empty and quiet

/image=sdxl=beach, sunset, golden hour, end of day

/image=sdxl=forest, midnight, moonlight filtering through trees
```

### Technique 7: Scale and Perspective

Manipulate viewer perspective:

```bash
/image=sdxl=mountain, aerial view, showing massive scale

/image=sdxl=insect, macro photography, extreme close-up

/image=sdxl=person in vast landscape, emphasizing isolation and scale
```

## Workflow Recommendations

### For Casual Users

```
1. Start with simple Flux prompts
2. Review enhanced captions to learn
3. Use SDXL occasionally for special images
4. Don't overthink it - have fun!
```

### For Creative Professionals

```
1. Flux: Rapid prototyping (5-10 concepts)
2. Review: Analyze which directions work
3. Flux: Refine promising concepts
4. SDXL: Create final high-quality versions
5. Document: Save successful prompts
```

### For Developers/Testers

```
1. Flux: Test feature functionality
2. Both: Verify model differences
3. Document: Note any issues or bugs
4. SDXL: Verify authentication flow
5. Monitor: Check queue behavior under load
```

### Daily Usage Tips

**Morning:**
- Quick concepts with Flux
- Explore new ideas
- Test different subjects

**Afternoon:**
- Refine successful morning concepts
- Start using SDXL for better versions
- Build on what worked

**Evening:**
- Final high-quality SDXL renders
- Polish and perfect
- Save favorites

### Project-Based Workflow

**Phase 1: Exploration (Flux)**
```bash
/image=flux=concept A
/image=flux=concept B
/image=flux=concept C
# Choose best direction
```

**Phase 2: Development (Flux + details)**
```bash
/image=flux=chosen concept, variation 1
/image=flux=chosen concept, variation 2
/image=flux=chosen concept, variation 3
# Refine details
```

**Phase 3: Production (SDXL)**
```bash
/image=sdxl=final concept, all details, high quality
# Create final deliverable
```

## Measuring Success

### Good Result Indicators

✅ Image matches your mental concept  
✅ Enhanced prompt makes sense  
✅ Quality appropriate for use case  
✅ Generated within expected time  
✅ No artifacts or errors  

### Improvement Signals

📈 Getting better results with less iteration  
📈 Understanding which prompts work  
📈 Faster concept-to-final workflow  
📈 Rarely hitting rate limits  
📈 Choosing right model first time  

### Success Metrics

Track your improvement:
- Time from concept to final: Decreasing
- Iterations per final image: Decreasing
- Satisfaction with results: Increasing
- Prompt writing speed: Increasing
- Model selection accuracy: Increasing

---

**Next Steps:**
- [Command Reference](command-reference.md) - Complete command documentation
- [Troubleshooting](../troubleshooting/common-issues.md) - Solve problems
- [API Reference](../api/prompt-enhancer.md) - Technical details
