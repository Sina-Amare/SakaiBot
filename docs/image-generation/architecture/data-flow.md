# Data Flow

**Last Updated:** 2024-01-15  
**Audience:** Developers, Architects  
**Purpose:** Sequence diagrams and data transformation flows

## Table of Contents

- [Complete Request Flow](#complete-request-flow)
- [Queue Processing Flow](#queue-processing-flow)
- [Prompt Enhancement Flow](#prompt-enhancement-flow)
- [Error Handling Flow](#error-handling-flow)
- [Concurrent Processing Flow](#concurrent-processing-flow)
- [Data Transformations](#data-transformations)

## Complete Request Flow

### Sequence Diagram

```
User          Handler         Queue           Enhancer        Generator       Worker
 |              |              |                |               |              |
 |--/image=-->  |              |                |               |              |
 |              |              |                |               |              |
 |              |--validate--> |                |               |              |
 |              |              |                |               |              |
 |              |--add_req---> |                |               |              |
 |              |              |                |               |              |
 |<--status msg-|              |                |               |              |
 |              |              |                |               |              |
 |              |--try_start-->|                |               |              |
 |              |<--success----|                |               |              |
 |              |              |                |               |              |
 |              |--enhance---->|                |               |              |
 |              |              |--LLM call----> |               |              |
 |              |              |<--enhanced-----|               |              |
 |              |<--prompt-----|                |               |              |
 |              |              |                |               |              |
 |              |--generate--->|                |               |              |
 |              |              |                |--HTTP req---> |              |
 |              |              |                |               |--worker----> |
 |              |              |                |               |              |--AI gen-->
 |              |              |                |               |              |
 |              |              |                |               |<--image------|
 |              |              |                |<--saved-------|              |
 |              |<--path-------|                |               |              |
 |              |              |                |               |              |
 |              |--mark_done-->|                |               |              |
 |              |              |                |               |              |
 |<--[IMAGE]----|              |                |               |              |
 |              |              |                |               |              |
```

### Step-by-Step Flow

#### Phase 1: Command Reception

```
1. User sends: /image=flux=cat
   
2. Telegram delivers message to SakaiBot
   
3. Telethon client triggers event handler
   
4. Event router identifies /image command
   
5. Routes to ImageHandler.handle_image_command()
```

**Data at this stage:**
- Message object (Telethon)
- Raw text: "/image=flux=cat"
- User ID, Chat ID, Message ID

#### Phase 2: Parsing & Validation

```
6. ImageHandler._parse_image_command()
   Input:  "/image=flux=cat"
   Output: {"model": "flux", "prompt": "cat"}
   
7. InputValidator.validate_image_model("flux")
   Check: "flux" in ["flux", "sdxl"] → True
   
8. InputValidator.validate_image_prompt("cat")
   - Remove control chars
   - Check length (1-1000)
   - Sanitize
   Output: "cat"
   
9. Rate limiter check
   User 123456: 3/10 requests used
   Remaining: 7
   Status: ALLOWED
```

**Data at this stage:**
- Validated model: "flux"
- Sanitized prompt: "cat"
- User quota remaining: 7

#### Phase 3: Queue Addition

```
10. image_queue.add_request("flux", "cat", user_id=123456)
    
11. Generate request ID: "img_a1b2c3d4"
    
12. Create ImageRequest:
    {
      request_id: "img_a1b2c3d4",
      model: "flux",
      prompt: "cat",
      user_id: 123456,
      status: PENDING
    }
    
13. Add to _flux_queue: [Request_a1b2c3d4]
    
14. Store in _requests: {"img_a1b2c3d4": Request_a1b2c3d4}
    
15. Return request_id: "img_a1b2c3d4"
```

**Data at this stage:**
- Request ID: "img_a1b2c3d4"
- Queue position: 1
- Status: PENDING

#### Phase 4: Queue Wait

```
16. Send status: "🎨 Processing image request with FLUX..."
    
17. Loop every 2 seconds:
    
    Iteration 1:
    - try_start_processing("img_a1b2c3d4", "flux")
    - Check: _flux_processing == False? YES
    - Check: Next pending == "img_a1b2c3d4"? YES
    - Set status = PROCESSING
    - Set _flux_processing = True
    - Return True → BREAK LOOP
```

**If queue was busy:**
```
    Iteration 1:
    - try_start_processing() → False (busy)
    - get_queue_position() → 2
    - Edit message: "⏳ In FLUX queue: position 2..."
    - Sleep 2 seconds
    
    Iteration 2:
    - try_start_processing() → True (our turn!)
    - BREAK LOOP
```

**Data at this stage:**
- Status: PROCESSING
- _flux_processing: True
- Position: 1 (currently processing)

#### Phase 5: Prompt Enhancement

```
18. Update status: "🎨 Enhancing prompt with AI..."
    
19. prompt_enhancer.enhance_prompt("cat")
    
20. Format enhancement request:
    System: "You are an expert at image prompts..."
    User: "Enhance: cat"
    
21. ai_processor.execute_custom_prompt()
    → Calls OpenRouter/Gemini API
    → Waits 3-5 seconds
    
22. LLM response:
    "A beautiful orange tabby cat sitting on a 
     windowsill, soft natural lighting, photorealistic 
     style, detailed fur texture, peaceful atmosphere"
    
23. Clean response (remove markdown, validate)
    
24. Return enhanced prompt
```

**Data at this stage:**
- Original: "cat"
- Enhanced: "A beautiful orange tabby cat..."
- Duration: ~4 seconds

#### Phase 6: Image Generation

```
25. Update status: "🖼️ Generating image with FLUX..."
    
26. image_generator.generate_with_flux(enhanced_prompt)
    
27. Build request URL:
    https://worker.dev?prompt=A%20beautiful%20orange...
    
28. Send HTTP GET request
    
29. Cloudflare Worker:
    - Receives prompt
    - Calls Flux AI model
    - Generates image (5-10 seconds)
    - Returns PNG binary
    
30. Receive response:
    Status: 200 OK
    Content-Type: image/png
    Body: [PNG bytes]
    
31. Save to disk:
    File: temp/images/image_flux_a1b2c3d4_1705334567.png
    Size: 2.4 MB
    
32. Return: (True, "/path/to/image.png", None)
```

**Data at this stage:**
- Image saved: temp/images/image_flux_...png
- File size: ~2-5 MB
- Duration: ~8 seconds

#### Phase 7: Completion

```
33. image_queue.mark_completed("img_a1b2c3d4", "/path/to/image.png")
    - Set status = COMPLETED
    - Set image_path = "/path/to/image.png"
    - Set _flux_processing = False
    
34. Build caption:
    "🎨 Image generated with FLUX\n\n"
    "Enhanced prompt:\n"
    "[Enhanced prompt up to 1024 chars]"
    
35. Update status: "📤 Sending image..."
    
36. client.send_file(chat_id, image_path, caption=caption)
    - Upload to Telegram
    - Duration: 1-2 seconds
    
37. Delete status message
    
38. Clean up temp file:
    os.remove("/path/to/image.png")
```

**Data at this stage:**
- Image delivered to user
- Temp file deleted
- Queue freed for next request

### Timing Breakdown

```
Total Time: ~15-25 seconds

Breakdown:
- Parsing & validation:     <1s
- Queue wait:               0-30s (depends on queue)
- Prompt enhancement:       3-5s
- Image generation:         5-15s (Flux), 10-15s (SDXL)
- Image upload:             1-2s
- Cleanup:                  <1s
```

## Queue Processing Flow

### Single Request (No Wait)

```
Timeline: 0s ─────────────────────────────────────> 15s

0s:  Request added to queue
     Status: PENDING
     Queue: [Request_A]
     
0s:  try_start_processing() → Success immediately
     Status: PROCESSING
     _flux_processing: True
     
4s:  Prompt enhancement completes
     
12s: Image generation completes
     
14s: Image uploaded
     
15s: mark_completed()
     Status: COMPLETED
     _flux_processing: False
     Queue: [Request_A (completed)]
```

### Multiple Sequential Requests

```
Timeline: 0s ──────────────────────────────────────> 45s

Request A (arrives at 0s):
0s:  Added, try_start → Success
     Processing: A
     Queue: [A-PROCESSING]

Request B (arrives at 2s):
2s:  Added, try_start → False (A is processing)
     Queue: [A-PROCESSING, B-PENDING]
     Position: 2
     
4s:  try_start → False
     Position: 2
     
6s:  try_start → False
     Position: 2

15s: A completes
     _flux_processing: False
     Queue: [A-COMPLETED, B-PENDING]

16s: B: try_start → Success!
     Processing: B
     Queue: [A-COMPLETED, B-PROCESSING]

Request C (arrives at 20s):
20s: Added, try_start → False
     Queue: [A-COMPLETED, B-PROCESSING, C-PENDING]
     Position: 2

30s: B completes
     _flux_processing: False

31s: C: try_start → Success!
     Processing: C
     
45s: C completes
```

### Concurrent Different Models

```
Timeline: 0s ──────────────────────────────────────> 20s

Request A - Flux (arrives at 0s):
0s:  Added to Flux queue
     try_start(Flux) → Success
     _flux_processing: True
     
     Flux Queue: [A-PROCESSING]
     SDXL Queue: []

Request B - SDXL (arrives at 1s):
1s:  Added to SDXL queue
     try_start(SDXL) → Success!  (Different model!)
     _sdxl_processing: True
     
     Flux Queue: [A-PROCESSING]
     SDXL Queue: [B-PROCESSING]
     
     ↓ Both processing simultaneously ↓

15s: A (Flux) completes
     _flux_processing: False
     Flux Queue: [A-COMPLETED]

18s: B (SDXL) completes
     _sdxl_processing: False
     SDXL Queue: [B-COMPLETED]
```

## Prompt Enhancement Flow

### Successful Enhancement

```
Input Prompt: "cat"

Step 1: Check Configuration
  ┌─────────────────────────────┐
  │ is_configured?              │
  │ LLM Provider: OpenRouter    │
  │ API Key: ***********        │
  │ Status: CONFIGURED ✓        │
  └─────────────────────────────┘
         ↓
         
Step 2: Format Prompt
  ┌─────────────────────────────┐
  │ System Message:             │
  │ "You are an expert at..."   │
  │                             │
  │ User Message:               │
  │ "Enhance: cat"              │
  └─────────────────────────────┘
         ↓
         
Step 3: LLM Call
  ┌─────────────────────────────┐
  │ POST /chat/completions      │
  │ Model: gemini-2.0-flash     │
  │ Temperature: 0.7            │
  │ Max Tokens: 150             │
  └─────────────────────────────┘
         ↓ (3-5 seconds)
         
Step 4: Receive Response
  ┌─────────────────────────────┐
  │ "A beautiful orange tabby   │
  │  cat sitting on a           │
  │  windowsill, soft natural   │
  │  lighting..."               │
  └─────────────────────────────┘
         ↓
         
Step 5: Clean Output
  - Remove markdown: ``` blocks
  - Trim whitespace
  - Remove explanations
  - Validate non-empty
         ↓
         
Step 6: Validate Length
  Length: 187 chars
  Max: 1000 chars
  Status: OK ✓
         ↓
         
Step 7: Return
  "A beautiful orange tabby cat sitting on a 
   windowsill, soft natural lighting, 
   photorealistic style, detailed fur texture, 
   peaceful atmosphere"
```

### Enhancement with Fallback

```
Input Prompt: "mountain"

Step 1: Check Configuration
  Status: CONFIGURED ✓
         ↓
         
Step 2-3: LLM Call
  (Network timeout after 30s)
         ↓
         
Step 4: Catch Exception
  ┌─────────────────────────────┐
  │ Exception: TimeoutError     │
  │ "LLM request timed out"     │
  └─────────────────────────────┘
         ↓
         
Step 5: Fallback
  ┌─────────────────────────────┐
  │ LOG: "Enhancement failed,   │
  │       using original"       │
  │                             │
  │ RETURN: "mountain"          │
  └─────────────────────────────┘
```

### No LLM Configured

```
Input Prompt: "sunset"

Step 1: Check Configuration
  ┌─────────────────────────────┐
  │ is_configured?              │
  │ Status: NOT CONFIGURED ✗    │
  └─────────────────────────────┘
         ↓
         
Step 2: Immediate Fallback
  ┌─────────────────────────────┐
  │ LOG: "LLM not configured"   │
  │                             │
  │ RETURN: "sunset"            │
  │ (original unchanged)        │
  └─────────────────────────────┘
```

## Error Handling Flow

### Network Error with Retry

```
Request: generate_with_flux("prompt")

Attempt 1 (0s):
  ┌─────────────────────────────┐
  │ HTTP GET to worker         │
  │ → ConnectionError          │
  │ "Failed to connect"        │
  └─────────────────────────────┘
         ↓
  @retry_with_backoff catches
         ↓
  Wait 1 second
         ↓

Attempt 2 (1s):
  ┌─────────────────────────────┐
  │ HTTP GET to worker         │
  │ → TimeoutError             │
  │ "Request timed out"        │
  └─────────────────────────────┘
         ↓
  Wait 2 seconds (exponential)
         ↓

Attempt 3 (3s):
  ┌─────────────────────────────┐
  │ HTTP GET to worker         │
  │ → 200 OK                   │
  │ Success! ✓                 │
  └─────────────────────────────┘
         ↓
  Return image
```

### Client Error (No Retry)

```
Request: generate_with_sdxl("prompt")

Attempt 1:
  ┌─────────────────────────────┐
  │ HTTP POST to worker        │
  │ Status: 401 Unauthorized   │
  └─────────────────────────────┘
         ↓
  Check status code
         ↓
  ┌─────────────────────────────┐
  │ if status == 401:          │
  │   return (False, None,     │
  │     "Invalid API key")     │
  └─────────────────────────────┘
         ↓
  NO RETRY (client error)
         ↓
  Return error to handler
         ↓
  ┌─────────────────────────────┐
  │ ImageHandler receives:     │
  │ (False, None, "Invalid...") │
  │                            │
  │ mark_failed()              │
  │ Send error to user:        │
  │ "🔐 Authentication error"  │
  └─────────────────────────────┘
```

### Complete Error Flow

```
Any Component
     ↓ Exception
     │
     ├─→ Catch in component
     │   └─→ Log with logger.error()
     │       └─→ Return error tuple/None
     │
     ↓ Error propagates
     │
ImageHandler
     ↓ Receives error
     │
     ├─→ Log with ErrorHandler.log_error()
     │   └─→ Sanitize sensitive data
     │       └─→ Write to log file
     │
     ├─→ Get user message
     │   └─→ ErrorHandler.get_user_message()
     │       └─→ Map to friendly message
     │
     ├─→ Mark request failed
     │   └─→ image_queue.mark_failed()
     │       └─→ Update status
     │       └─→ Release processing flag
     │
     └─→ Send to user
         └─→ client.edit_message()
             └─→ User sees friendly error
```

## Concurrent Processing Flow

### Timeline View

```
Time: 0s ──────────────────────────────────────────────> 30s

User A: /image=flux=cat (0s)
├─ Queue Flux [A]
├─ Start processing A
├─ Enhance (0s-4s)
├─ Generate (4s-12s)
├─ Send (12s-14s)
└─ Complete (14s)

User B: /image=sdxl=dog (2s)
├─ Queue SDXL [B]
├─ Start processing B (concurrent!)
├─ Enhance (2s-6s)
├─ Generate (6s-18s)
├─ Send (18s-20s)
└─ Complete (20s)

User C: /image=flux=bird (5s)
├─ Queue Flux [A-proc, C-pending]
├─ Wait... position 2
├─ Wait... position 2
├─ A completes (14s)
├─ Start processing C (14s)
├─ Enhance (14s-18s)
├─ Generate (18s-26s)
├─ Send (26s-28s)
└─ Complete (28s)

User D: /image=sdxl=fish (10s)
├─ Queue SDXL [B-proc, D-pending]
├─ Wait... position 2
├─ Wait... position 2
├─ B completes (20s)
├─ Start processing D (20s)
├─ Enhance (20s-24s)
├─ Generate (24s-36s)
└─ Complete (36s)
```

### Parallel Execution

```
            Time →
Model    0s    5s    10s   15s   20s   25s   30s
─────────────────────────────────────────────────
Flux    [███ A ███]       [██ C ██]
SDXL           [████ B ████]       [████ D ████]
─────────────────────────────────────────────────
Active     A     A,B    B,C    C     D      D
Count      1      2      2      1     1      1
```

**Key Points:**
- A and B process simultaneously (different models)
- C waits for A (same model)
- D waits for B (same model)
- Maximum 2 concurrent generations (1 per model)

## Data Transformations

### User Input → Request Object

```python
# Input
user_input = "/image=flux=cat"

# After parsing
parsed = {
    "model": "flux",
    "prompt": "cat"
}

# After validation
validated = {
    "model": "flux",  # lowercased, checked
    "prompt": "cat"   # sanitized, length-checked
}

# Request creation
request = ImageRequest(
    request_id="img_a1b2c3d4",      # generated
    model="flux",                    # validated
    prompt="cat",                    # sanitized
    user_id=123456,                  # from message
    status=ImageStatus.PENDING,      # initial
    image_path=None,                 # not yet generated
    error_message=None               # no error yet
)
```

### Prompt → Enhanced Prompt

```python
# Original
original = "cat"

# Enhancement request
llm_input = {
    "system": "You are an expert at image prompts...",
    "user": "Enhance the following prompt: cat"
}

# LLM output (raw)
llm_output = """
A beautiful orange tabby cat sitting on a windowsill,
soft natural lighting, photorealistic style, detailed
fur texture, peaceful atmosphere, shallow depth of field
"""

# After cleaning
cleaned = "A beautiful orange tabby cat sitting on a windowsill, soft natural lighting, photorealistic style, detailed fur texture, peaceful atmosphere, shallow depth of field"

# Final (validated)
enhanced = cleaned  # length OK, no markdown, valid
```

### HTTP Request → Image File

```python
# HTTP request
request = {
    "method": "GET",
    "url": "https://worker.dev?prompt=A%20beautiful%20cat...",
    "timeout": 120
}

# HTTP response
response = {
    "status": 200,
    "headers": {
        "content-type": "image/png",
        "content-length": "2456789"
    },
    "body": b'\x89PNG\r\n\x1a\n...'  # binary data
}

# File save
file_info = {
    "path": "temp/images/image_flux_a1b2c3d4_1705334567.png",
    "size": 2456789,
    "format": "PNG",
    "created": "2024-01-15T12:34:56Z"
}
```

### Status Updates Timeline

```python
# Timeline of status messages shown to user

t=0s:    "🎨 Processing image request with FLUX..."

t=0-14s: "⏳ In FLUX queue: position 2..."  (if waiting)

t=14s:   "🎨 Enhancing prompt with AI..."

t=18s:   "🖼️ Generating image with FLUX..."

t=26s:   "📤 Sending image..."

t=28s:   [Image received with caption]
         [Status message deleted]
```

---

**Next:** [Queue System](queue-system.md) for detailed queue mechanics
