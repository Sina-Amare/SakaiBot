# Component Design

**Last Updated:** 2024-01-15  
**Audience:** Developers, Architects  
**Complexity:** Technical Deep Dive

## Table of Contents

- [ImageHandler Component](#imagehandler-component)
- [ImageQueue Component](#imagequeue-component)
- [PromptEnhancer Component](#promptenhancer-component)
- [ImageGenerator Component](#imagegenerator-component)
- [Supporting Components](#supporting-components)
- [Component Interactions](#component-interactions)

## ImageHandler Component

### Overview

**File:** `src/telegram/handlers/image_handler.py`  
**Lines of Code:** 436  
**Purpose:** Telegram command interface for image generation  
**Pattern:** Handler pattern with async processing

### Class Structure

```python
class ImageHandler(BaseHandler):
    """Handles image generation commands."""
    
    def __init__(
        self,
        ai_processor: AIProcessor,
        image_generator: ImageGenerator,
        prompt_enhancer: PromptEnhancer
    ):
        """Initialize with required dependencies."""
```

### Responsibilities

1. **Command Parsing**
   - Parse `/image=<model>=<prompt>` syntax
   - Extract model name and prompt
   - Validate command format

2. **Input Validation**
   - Validate model name (flux/sdxl)
   - Validate prompt (length, content)
   - Check rate limits

3. **Queue Management**
   - Add request to appropriate queue
   - Monitor queue position
   - Wait for processing turn

4. **Status Communication**
   - Send initial status
   - Update queue position
   - Show processing steps
   - Handle errors gracefully

5. **Image Delivery**
   - Upload image to Telegram
   - Include enhanced prompt as caption
   - Clean up temporary files

### Key Methods

#### `handle_image_command()`

**Purpose:** Entry point for command handling  
**Flow:**
```python
def handle_image_command(message, client, chat_id, sender_info):
    1. Parse command
    2. Validate model and prompt
    3. Check rate limit
    4. Create async task for processing
```

**Error Handling:**
- Invalid format → Usage help message
- Invalid model → List valid models
- Prompt validation fail → Error with reason
- Rate limit exceeded → Wait time message

#### `process_image_command()`

**Purpose:** Async processing of queued request  
**Flow:**
```python
async def process_image_command(...):
    1. Add to queue → get request_id
    2. Get queue position
    3. Send status message
    4. Loop:
       - Try to start processing
       - If not ready, update position
       - Wait 2 seconds
       - Repeat until processing starts
    5. Process the request
    6. Send image or error
```

**Queue Wait Loop:**
```python
while True:
    if image_queue.try_start_processing(request_id, model):
        break  # Our turn!
    
    # Update status
    position = image_queue.get_queue_position(request_id, model)
    if position > 1:
        await client.edit_message(msg, f"⏳ Position {position}...")
    
    await asyncio.sleep(2)
```

#### `_process_single_request()`

**Purpose:** Execute the actual generation  
**Flow:**
```python
async def _process_single_request(...):
    1. Update status: "Enhancing prompt..."
    2. Call prompt_enhancer.enhance_prompt()
    3. Update status: "Generating image..."
    4. Call image_generator.generate_with_flux/sdxl()
    5. If success:
       - Mark completed
       - Send image
    6. If failure:
       - Mark failed
       - Send error message
```

**Error Recovery:**
- Enhancement failure → Use original prompt
- Generation failure → Send user-friendly error
- Network issues → Retry via generator
- Message edit fails → Send new message

#### `_send_image()`

**Purpose:** Upload image to Telegram  
**Flow:**
```python
async def _send_image(...):
    1. Build caption with enhanced prompt
    2. Truncate if > 1024 chars (Telegram limit)
    3. Upload image with client.send_file()
    4. Delete status message
    5. Clean up temp file
```

**Caption Format:**
```
🎨 Image generated with FLUX

Enhanced prompt:
[Enhanced prompt text up to 1024 chars]
```

### Dependencies

```python
# External
from telethon import TelegramClient
from telethon.tl.types import Message

# Internal
from ...ai.image_generator import ImageGenerator
from ...ai.image_queue import image_queue
from ...ai.prompt_enhancer import PromptEnhancer
from ...utils.rate_limiter import get_ai_rate_limiter
from ...utils.metrics import get_metrics_collector
from ...utils.error_handler import ErrorHandler
```

### State Management

**No persistent state** - all state is in:
- ImageQueue (global singleton)
- Message objects (Telegram)
- Temporary files (disk)

### Metrics Tracked

```python
metrics.increment('image_command.requests', tags={'model': model})
metrics.increment('image_command.success', tags={'model': model})
metrics.increment('image_command.errors', tags={'model': model, 'error_type': ...})
metrics.increment('image_command.rate_limited', tags={'model': model})
```

### Performance Characteristics

- **Memory:** ~5MB per active request (message buffers)
- **CPU:** Minimal (mostly I/O wait)
- **Network:** Heavy during image upload
- **Concurrency:** Unlimited handlers, queue controls generation

## ImageQueue Component

### Overview

**File:** `src/ai/image_queue.py`  
**Lines of Code:** 359  
**Purpose:** Manage separate FIFO queues for Flux and SDXL  
**Pattern:** Singleton with synchronized access

### Design Philosophy

**Key Decision:** Separate queues per model

**Rationale:**
- Flux and SDXL have different characteristics
- Users should not wait for different model
- FIFO guarantees within each model
- Concurrent processing across models

**Example:**
```
User A: /image=flux=prompt1  → Flux queue [processing]
User B: /image=sdxl=prompt2  → SDXL queue [processing] (concurrent!)
User C: /image=flux=prompt3  → Flux queue [waiting for A]
```

### Data Structures

#### ImageStatus Enum

```python
class ImageStatus(Enum):
    PENDING = "pending"      # In queue, not started
    PROCESSING = "processing" # Currently generating
    COMPLETED = "completed"   # Successfully done
    FAILED = "failed"         # Error occurred
```

#### ImageRequest Dataclass

```python
@dataclass
class ImageRequest:
    request_id: str           # Unique ID (img_<uuid>)
    model: str                # "flux" or "sdxl"
    prompt: str               # User's original prompt
    user_id: int              # Telegram user ID
    status: ImageStatus       # Current status
    image_path: Optional[str] # Path when completed
    error_message: Optional[str]  # Error if failed
```

#### Queue Storage

```python
class ImageQueue:
    def __init__(self):
        # Separate queues
        self._flux_queue: List[ImageRequest] = []
        self._sdxl_queue: List[ImageRequest] = []
        
        # Processing flags
        self._flux_processing: bool = False
        self._sdxl_processing: bool = False
        
        # Fast lookup
        self._requests: Dict[str, ImageRequest] = {}
```

### Key Methods

#### `add_request()`

**Purpose:** Add new request to appropriate queue

```python
def add_request(self, model: str, prompt: str, user_id: int) -> str:
    # Generate unique ID
    request_id = f"img_{uuid.uuid4().hex[:8]}"
    
    # Create request object
    request = ImageRequest(
        request_id=request_id,
        model=model,
        prompt=prompt,
        user_id=user_id
    )
    
    # Store in lookup dict
    self._requests[request_id] = request
    
    # Add to appropriate queue
    if model == "flux":
        self._flux_queue.append(request)
    elif model == "sdxl":
        self._sdxl_queue.append(request)
    
    return request_id
```

**Thread Safety:** Single-threaded Python, no locks needed

#### `try_start_processing()`

**Purpose:** Atomically check and start processing

```python
def try_start_processing(self, request_id: str, model: str) -> bool:
    # Check if already processing this model
    if model == "flux":
        if self._flux_processing:
            return False  # Busy
        
        # Check if this is the next request
        next_request = self.get_next_pending("flux")
        if next_request and next_request.request_id == request_id:
            # It's our turn!
            next_request.status = ImageStatus.PROCESSING
            self._flux_processing = True
            return True
    
    # Similar for SDXL...
    return False
```

**Critical Section:** This method ensures:
1. Only one request processes per model
2. Only the next pending request can start
3. FIFO order is maintained

#### `get_queue_position()`

**Purpose:** Calculate position in queue

```python
def get_queue_position(self, request_id: str, model: str) -> Optional[int]:
    queue = self._flux_queue if model == "flux" else self._sdxl_queue
    
    position = 1
    for req in queue:
        if req.request_id == request_id:
            return position
        if req.status == ImageStatus.PENDING:
            position += 1
    
    return None
```

**Complexity:** O(n) where n = queue length

#### `mark_completed()` / `mark_failed()`

**Purpose:** Update request status and release lock

```python
def mark_completed(self, request_id: str, image_path: str):
    request = self._requests[request_id]
    request.status = ImageStatus.COMPLETED
    request.image_path = image_path
    
    # Release processing flag
    if request.model == "flux":
        self._flux_processing = False
    elif request.model == "sdxl":
        self._sdxl_processing = False
```

**Important:** Always called to release processing flag

### Queue Behavior

#### FIFO Within Model

```
Flux Queue:
Request 1 [PROCESSING] ← Currently generating
Request 2 [PENDING]    ← Next in line
Request 3 [PENDING]    ← Waiting

SDXL Queue:
Request 4 [PROCESSING] ← Also generating (concurrent!)
Request 5 [PENDING]    ← Next for SDXL
```

#### Concurrent Cross-Model

```
Time: 0s
Flux: Request A starts [PROCESSING]
SDXL: Request B starts [PROCESSING]  ← Both process at same time

Time: 10s
Flux: Request A completes
Flux: Request C starts [PROCESSING]
SDXL: Request B still processing...

Time: 15s
SDXL: Request B completes
SDXL: Request D starts [PROCESSING]
```

### Global Singleton

```python
# Global instance
image_queue = ImageQueue()

# Usage everywhere
from src.ai.image_queue import image_queue
request_id = image_queue.add_request(...)
```

**Why Singleton:**
- Single source of truth
- No race conditions between handlers
- Simple state management

## PromptEnhancer Component

### Overview

**File:** `src/ai/prompt_enhancer.py`  
**Lines of Code:** 99  
**Purpose:** Enhance user prompts using LLM  
**Pattern:** Wrapper around AIProcessor

### Enhancement Strategy

**Philosophy:** Always try, fallback gracefully

```
User Prompt → Try Enhancement → Success? → Enhanced Prompt
                     ↓
                   Failure → Original Prompt
```

### Class Structure

```python
class PromptEnhancer:
    def __init__(self, ai_processor: AIProcessor):
        self._ai_processor = ai_processor
        self._logger = get_logger(self.__class__.__name__)
```

### Key Method: `enhance_prompt()`

**Purpose:** Enhance or fallback gracefully

```python
async def enhance_prompt(self, user_prompt: str) -> str:
    # Check if LLM configured
    if not self._ai_processor.is_configured:
        return user_prompt  # Fallback
    
    try:
        # Format enhancement prompt
        enhancement_prompt = IMAGE_PROMPT_ENHANCEMENT_PROMPT.format(
            user_prompt=user_prompt
        )
        
        # Call LLM
        enhanced = await self._ai_processor.execute_custom_prompt(
            user_prompt=enhancement_prompt,
            system_message=IMAGE_PROMPT_ENHANCEMENT_SYSTEM_MESSAGE
        )
        
        # Validate response
        if not enhanced or not enhanced.strip():
            return user_prompt  # Fallback
        
        # Clean output
        enhanced = self._clean_enhanced_output(enhanced)
        
        # Validate length
        if len(enhanced) > MAX_IMAGE_PROMPT_LENGTH:
            enhanced = self._truncate_prompt(enhanced)
        
        return enhanced
        
    except Exception as e:
        self._logger.warning(f"Enhancement failed: {e}")
        return user_prompt  # Always fallback
```

### Output Cleaning

**Problem:** LLM may return extra formatting

```python
def _clean_enhanced_output(self, text: str) -> str:
    # Remove markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    
    # Remove explanatory text
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        # Find the actual enhanced prompt
        if line and len(line) > 10 and not line.startswith(("Enhanced", "Here", "The")):
            return line
    
    return text
```

### Enhancement Prompts

Located in `src/ai/prompts.py`:

```python
IMAGE_PROMPT_ENHANCEMENT_SYSTEM_MESSAGE = """
You are an expert at creating detailed and effective prompts 
for AI image generation. Enhance user prompts while maintaining 
the core concept.

Guidelines:
- Keep original concept intact
- Add lighting, style, composition details
- Use clear, descriptive language
- Aim for 50-150 words
- Respond ONLY with enhanced prompt
"""

IMAGE_PROMPT_ENHANCEMENT_PROMPT = """
Enhance the following image generation prompt:

Original prompt: {user_prompt}

Enhanced prompt:
"""
```

### Performance

- **Speed:** 3-5 seconds (LLM API call)
- **Reliability:** Always returns valid prompt
- **Quality:** Significantly improves results

### Example Transformations

```python
# Minimal input
"cat" 
→ "A beautiful orange tabby cat sitting on a windowsill, 
   soft natural lighting, photorealistic style, detailed 
   fur texture, peaceful atmosphere"

# Guided input
"sunset over ocean"
→ "Breathtaking sunset over calm ocean, vibrant orange 
   and pink sky, silhouette of palm trees, golden hour 
   lighting, serene mood, high quality photography"

# Detailed input (minor enhancement)
"professional portrait photograph of a woman, natural lighting"
→ "Professional portrait photograph of a woman with natural 
   window lighting, 50mm lens, shallow depth of field, warm 
   color grading, soft bokeh, magazine quality"
```

## ImageGenerator Component

### Overview

**File:** `src/ai/image_generator.py`  
**Lines of Code:** 259  
**Purpose:** HTTP communication with Cloudflare Workers  
**Pattern:** Async HTTP client with retry logic

### HTTP Client Management

```python
class ImageGenerator:
    def __init__(self):
        self._logger = get_logger(self.__class__.__name__)
        self._config = get_settings()
        self._http_client: Optional[httpx.AsyncClient] = None
```

#### Lazy Client Initialization

```python
def _get_http_client(self) -> httpx.AsyncClient:
    if self._http_client is None:
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=IMAGE_GENERATION_CONNECT_TIMEOUT,  # 30s
                read=IMAGE_GENERATION_TIMEOUT,              # 120s
                write=IMAGE_GENERATION_TIMEOUT,             # 120s
                pool=IMAGE_GENERATION_CONNECT_TIMEOUT       # 30s
            ),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            ),
            follow_redirects=True
        )
    return self._http_client
```

**Why Lazy:** Client created on first use, reused for all requests

### Flux Generation

#### Request Method

```python
async def _make_flux_request(self, prompt: str) -> httpx.Response:
    client = self._get_http_client()
    url = f"{self._config.flux_worker_url}?prompt={quote(prompt)}"
    
    try:
        response = await client.get(url)
        return response
    except httpx.TimeoutException as e:
        raise AIProcessorError("Image generation timed out")
    except httpx.RequestError as e:
        raise AIProcessorError(f"Network error: {e}")
```

**Request Format:**
```http
GET https://worker.dev?prompt=a%20beautiful%20cat
```

#### Generation Method

```python
@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
async def generate_with_flux(self, prompt: str) -> Tuple[bool, Optional[str], Optional[str]]:
    try:
        response = await self._make_flux_request(prompt)
        
        # Handle HTTP errors
        if response.status_code == 429:
            return (False, None, "Rate limit exceeded...")
        elif response.status_code == 400:
            return (False, None, "Invalid prompt...")
        elif response.status_code >= 500:
            return (False, None, "Service error...")
        elif response.status_code != 200:
            return (False, None, f"Failed with status {response.status_code}")
        
        # Validate content type
        content_type = response.headers.get("content-type", "").lower()
        if not content_type.startswith("image/"):
            return (False, None, "Invalid response format")
        
        # Save image
        image_path = self._save_image(response.content, "flux")
        return (True, image_path, None)
        
    except AIProcessorError as e:
        return (False, None, str(e))
```

**Return Format:** `(success, image_path, error_message)`

### SDXL Generation

#### Request Method

```python
async def _make_sdxl_request(self, prompt: str) -> httpx.Response:
    if not self._config.sdxl_api_key:
        raise AIProcessorError("SDXL API key not configured")
    
    client = self._get_http_client()
    url = self._config.sdxl_worker_url
    headers = {
        "Authorization": f"Bearer {self._config.sdxl_api_key}",
        "Content-Type": "application/json"
    }
    payload = {"prompt": prompt}
    
    try:
        response = await client.post(url, json=payload, headers=headers)
        return response
    except httpx.TimeoutException as e:
        raise AIProcessorError("Image generation timed out")
```

**Request Format:**
```http
POST https://worker.dev
Authorization: Bearer token_here
Content-Type: application/json

{"prompt": "a beautiful cat"}
```

#### Error Handling

```python
# SDXL-specific errors
if response.status_code == 401:
    return (False, None, "Invalid API key")
elif response.status_code == 405:
    return (False, None, "Invalid request method")
# ... plus all Flux errors
```

### Image Saving

```python
def _save_image(self, response_content: bytes, model_name: str) -> str:
    # Create directory
    temp_dir = Path(IMAGE_TEMP_DIR)  # temp/images
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    request_id = str(uuid.uuid4())[:8]
    timestamp = int(asyncio.get_event_loop().time())
    filename = f"image_{model_name}_{request_id}_{timestamp}.png"
    filepath = temp_dir / filename
    
    # Write file
    with open(filepath, 'wb') as f:
        f.write(response_content)
    
    return str(filepath)
```

**File Naming:** `image_flux_a1b2c3d4_1234567890.png`

### Retry Logic

Decorator provides automatic retry:

```python
@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
```

**Behavior:**
- Attempt 1: Immediate
- Attempt 2: Wait 1 second
- Attempt 3: Wait 2 seconds
- Attempt 4: Wait 4 seconds (capped at max_delay)

**Retry Conditions:**
- Network errors (connection, timeout)
- 5xx server errors
- Transient failures

**No Retry:**
- 4xx client errors (bad request, auth)
- Successful responses
- Content validation failures

## Supporting Components

### Configuration (config.py)

**Relevant Fields:**
```python
class Config(BaseSettings):
    flux_worker_url: str = Field(default=DEFAULT_FLUX_WORKER_URL)
    sdxl_worker_url: str = Field(default=DEFAULT_SDXL_WORKER_URL)
    sdxl_api_key: Optional[str] = Field(default=None)
    
    @property
    def is_image_generation_enabled(self) -> bool:
        flux_ok = bool(self.flux_worker_url and 
                      self.flux_worker_url.startswith("http"))
        sdxl_ok = bool(self.sdxl_worker_url and 
                      self.sdxl_api_key)
        return flux_ok or sdxl_ok
```

### Validators (validators.py)

```python
class InputValidator:
    @staticmethod
    def validate_image_model(model: str) -> bool:
        return model.lower() in SUPPORTED_IMAGE_MODELS
    
    @staticmethod
    def validate_image_prompt(prompt: str) -> str:
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', prompt)
        
        # Check length
        if len(sanitized) > MAX_IMAGE_PROMPT_LENGTH:
            raise ValueError("Prompt too long")
        
        # Check empty
        if not sanitized.strip():
            raise ValueError("Prompt empty")
        
        return sanitized.strip()
```

### Error Handler (error_handler.py)

**Image-Specific Errors:**
```python
if "image generation" in error_str:
    if "timeout" in error_str:
        return "⏱️ Image generation timed out..."
    elif "rate limit" in error_str:
        return "⚠️ Rate limit exceeded..."
    elif "authentication" in error_str:
        return "🔐 Authentication error..."
    # ... etc
```

## Component Interactions

### Complete Request Flow

```
User Command
    ↓
ImageHandler.handle_image_command()
    ↓ (parse & validate)
ImageHandler.process_image_command()
    ↓ (add to queue)
ImageQueue.add_request()
    ↓ (wait for turn)
ImageQueue.try_start_processing()
    ↓ (processing starts)
PromptEnhancer.enhance_prompt()
    ↓ (LLM call)
AIProcessor.execute_custom_prompt()
    ↓ (enhanced prompt ready)
ImageGenerator.generate_with_flux/sdxl()
    ↓ (HTTP request)
Cloudflare Worker
    ↓ (image binary)
ImageGenerator._save_image()
    ↓ (file saved)
ImageHandler._send_image()
    ↓ (Telegram upload)
User receives image
```

### Error Flow

```
Any Component Error
    ↓
ErrorHandler.log_error()  (logging)
    ↓
ErrorHandler.get_user_message()  (user-friendly)
    ↓
ImageHandler sends error to user
    ↓
ImageQueue.mark_failed()  (cleanup)
```

### Concurrent Flow

```
User A: /image=flux=cat
    ↓
Flux Queue [Request A - PROCESSING]
    ↓
Enhancement A → Generation A

User B: /image=sdxl=dog (sent during A)
    ↓
SDXL Queue [Request B - PROCESSING]  ← Parallel!
    ↓
Enhancement B → Generation B  ← Also parallel!

User C: /image=flux=bird (sent during A & B)
    ↓
Flux Queue [Request A - PROCESSING, Request C - PENDING]
    ↓
Waits for A to complete, then processes
```

---

**Next:** [Data Flow](data-flow.md) for sequence diagrams
