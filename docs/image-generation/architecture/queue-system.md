# Queue System Architecture

**Last Updated:** 2024-01-15  
**Audience:** Architects, Senior Developers  
**Complexity:** Advanced

## Table of Contents

- [Design Overview](#design-overview)
- [Queue Implementation](#queue-implementation)
- [FIFO Guarantees](#fifo-guarantees)
- [Concurrency Model](#concurrency-model)
- [State Management](#state-management)
- [Performance Analysis](#performance-analysis)

## Design Overview

### Core Principle

**Separate FIFO queues per model with concurrent cross-model processing.**

### Why Separate Queues?

#### Problem Without Separation

```
Single Global Queue:
[Flux-A, SDXL-B, Flux-C, SDXL-D]
       ↓
Processing: Flux-A (10s)
       ↓
Processing: SDXL-B (15s) ← Flux users wait for SDXL!
       ↓
Processing: Flux-C (10s) ← SDXL users wait for Flux!
```

**Issues:**
- Users waiting for different model type
- No parallelization opportunity
- Unfair wait times

#### Solution With Separation

```
Flux Queue:  [A, C]    → Process independently
SDXL Queue:  [B, D]    → Process independently
                ↓
Both can process simultaneously!
```

**Benefits:**
- ✅ Fair queuing within model
- ✅ No cross-model blocking
- ✅ Concurrent processing
- ✅ Better resource utilization

### Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│              ImageQueue (Singleton)             │
├─────────────────────────────────────────────────┤
│                                                 │
│  Flux Queue                SDXL Queue           │
│  ┌──────────┐              ┌──────────┐        │
│  │ Request A│              │ Request B│        │
│  │ PENDING  │              │PROCESSING│        │
│  └──────────┘              └──────────┘        │
│  ┌──────────┐              ┌──────────┐        │
│  │ Request C│              │ Request D│        │
│  │PROCESSING│              │ PENDING  │        │
│  └──────────┘              └──────────┘        │
│  ┌──────────┐                                   │
│  │ Request E│                                   │
│  │ PENDING  │                                   │
│  └──────────┘                                   │
│                                                 │
│  _flux_processing: True                         │
│  _sdxl_processing: True                         │
│                                                 │
│  Request Lookup:                                │
│  {                                              │
│    "img_a1b2": Request A,                       │
│    "img_c3d4": Request B,                       │
│    ...                                          │
│  }                                              │
└─────────────────────────────────────────────────┘
```

## Queue Implementation

### Data Structures

#### Request Status

```python
class ImageStatus(Enum):
    """Lifecycle states of an image request."""
    
    PENDING = "pending"        # Waiting in queue
    PROCESSING = "processing"  # Currently generating
    COMPLETED = "completed"    # Successfully finished
    FAILED = "failed"          # Error occurred
```

**State Transitions:**
```
PENDING → PROCESSING → COMPLETED
            ↓
          FAILED
```

#### Request Object

```python
@dataclass
class ImageRequest:
    """Represents a single image generation request."""
    
    request_id: str              # Unique identifier
    model: str                   # "flux" or "sdxl"
    prompt: str                  # Original user prompt
    user_id: int                 # Telegram user ID
    status: ImageStatus          # Current status
    image_path: Optional[str]    # Path when completed
    error_message: Optional[str] # Error if failed
```

**Example:**
```python
request = ImageRequest(
    request_id="img_a1b2c3d4",
    model="flux",
    prompt="cat",
    user_id=123456,
    status=ImageStatus.PENDING,
    image_path=None,
    error_message=None
)
```

#### Queue Storage

```python
class ImageQueue:
    """Global queue manager."""
    
    def __init__(self):
        # Separate queues for each model
        self._flux_queue: List[ImageRequest] = []
        self._sdxl_queue: List[ImageRequest] = []
        
        # Processing locks (boolean flags)
        self._flux_processing: bool = False
        self._sdxl_processing: bool = False
        
        # Fast request lookup
        self._requests: Dict[str, ImageRequest] = {}
```

**Memory Layout:**
```
_flux_queue:  [ptr_A, ptr_C, ptr_E]  ← References to ImageRequest
_sdxl_queue:  [ptr_B, ptr_D]         ← References to ImageRequest
_requests:    {
                "img_a1b2": Request_A,  ← Actual objects
                "img_c3d4": Request_C,
                ...
              }
```

### Core Operations

#### 1. Add Request

```python
def add_request(self, model: str, prompt: str, user_id: int) -> str:
    """
    Add request to appropriate queue.
    
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    # Generate unique ID
    request_id = f"img_{uuid.uuid4().hex[:8]}"
    
    # Create request
    request = ImageRequest(
        request_id=request_id,
        model=model,
        prompt=prompt,
        user_id=user_id
    )
    
    # Store for fast lookup
    self._requests[request_id] = request
    
    # Add to model-specific queue
    if model == "flux":
        self._flux_queue.append(request)
        position = len(self._flux_queue)
    elif model == "sdxl":
        self._sdxl_queue.append(request)
        position = len(self._sdxl_queue)
    
    self._logger.info(
        f"Added {model} request {request_id} to queue (position: {position})"
    )
    
    return request_id
```

**Example:**
```python
# User sends /image=flux=cat
request_id = queue.add_request("flux", "cat", 123456)
# Returns: "img_a1b2c3d4"
# Flux queue now: [Request_a1b2c3d4]
```

#### 2. Try Start Processing

```python
def try_start_processing(self, request_id: str, model: str) -> bool:
    """
    Atomically check if request can start processing.
    
    Returns:
        True if processing started
        False if must wait
    
    Time Complexity: O(n) where n = queue length
    """
    if model == "flux":
        # Check if Flux is busy
        if self._flux_processing:
            return False  # Another Flux request is processing
        
        # Get next pending request
        next_request = self.get_next_pending("flux")
        
        # Check if this request is next in line
        if next_request and next_request.request_id == request_id:
            # It's our turn!
            next_request.status = ImageStatus.PROCESSING
            self._flux_processing = True
            self._logger.info(f"Started processing Flux {request_id}")
            return True
    
    elif model == "sdxl":
        # Similar logic for SDXL
        if self._sdxl_processing:
            return False
        
        next_request = self.get_next_pending("sdxl")
        if next_request and next_request.request_id == request_id:
            next_request.status = ImageStatus.PROCESSING
            self._sdxl_processing = True
            self._logger.info(f"Started processing SDXL {request_id}")
            return True
    
    return False
```

**Critical Properties:**
1. **Mutual Exclusion:** Only one request processes per model
2. **FIFO Order:** Only next pending request can start
3. **Atomicity:** Check-and-set in single operation

**Example:**
```python
# Queue: [A-PENDING, B-PENDING]
# _flux_processing = False

# Try to start B (not first)
queue.try_start_processing("img_b", "flux")
# Returns: False (A is ahead)

# Try to start A (first)
queue.try_start_processing("img_a", "flux")
# Returns: True
# A.status = PROCESSING
# _flux_processing = True

# Try to start A again
queue.try_start_processing("img_a", "flux")
# Returns: False (already processing)
```

#### 3. Get Queue Position

```python
def get_queue_position(self, request_id: str, model: str) -> Optional[int]:
    """
    Calculate position in queue (1-based).
    
    Only counts PENDING requests ahead of this one.
    
    Time Complexity: O(n)
    Returns: None if not in queue or not pending
    """
    request = self._requests.get(request_id)
    if not request or request.model != model:
        return None
    
    if request.status != ImageStatus.PENDING:
        return None  # Not waiting, either processing or done
    
    # Get appropriate queue
    queue = self._flux_queue if model == "flux" else self._sdxl_queue
    
    # Count position
    position = 1
    for req in queue:
        if req.request_id == request_id:
            return position
        # Only count pending requests
        if req.status == ImageStatus.PENDING:
            position += 1
    
    return None
```

**Example:**
```python
# Queue: [A-PROCESSING, B-PENDING, C-PENDING, D-COMPLETED]

queue.get_queue_position("A", "flux")  # None (processing)
queue.get_queue_position("B", "flux")  # 1 (next)
queue.get_queue_position("C", "flux")  # 2 (after B)
queue.get_queue_position("D", "flux")  # None (completed)
```

#### 4. Mark Completed/Failed

```python
def mark_completed(self, request_id: str, image_path: str):
    """
    Mark request as completed and release lock.
    
    Time Complexity: O(1)
    """
    request = self._requests.get(request_id)
    if not request:
        return
    
    # Update status
    request.status = ImageStatus.COMPLETED
    request.image_path = image_path
    
    # Release processing flag
    if request.model == "flux":
        self._flux_processing = False
    elif request.model == "sdxl":
        self._sdxl_processing = False
    
    self._logger.info(f"Request {request_id} completed")

def mark_failed(self, request_id: str, error_message: str):
    """
    Mark request as failed and release lock.
    
    Time Complexity: O(1)
    """
    request = self._requests.get(request_id)
    if not request:
        return
    
    # Update status
    request.status = ImageStatus.FAILED
    request.error_message = error_message
    
    # Release processing flag
    if request.model == "flux":
        self._flux_processing = False
    elif request.model == "sdxl":
        self._sdxl_processing = False
    
    self._logger.error(f"Request {request_id} failed: {error_message}")
```

**Critical:** Always called to release processing flag, allowing next request.

## FIFO Guarantees

### Ordering Rules

**Rule 1: Requests are processed in order of arrival within each model.**

```python
# Arrivals
t=0s: User A → /image=flux=cat   → Added to Flux queue position 1
t=2s: User B → /image=flux=dog   → Added to Flux queue position 2
t=5s: User C → /image=flux=bird  → Added to Flux queue position 3

# Processing order
1. Cat  (User A, arrived first)
2. Dog  (User B, arrived second)
3. Bird (User C, arrived third)
```

**Rule 2: Different models don't affect each other's order.**

```python
# Arrivals
t=0s: User A → /image=flux=cat   → Flux queue [A]
t=1s: User B → /image=sdxl=dog   → SDXL queue [B]
t=2s: User C → /image=flux=bird  → Flux queue [A, C]

# Processing
- A and B process concurrently (different models)
- C waits for A, not affected by B
```

### Enforcement Mechanism

#### try_start_processing() Logic

```python
def try_start_processing(request_id, model):
    # Only next PENDING request can start
    next_pending = get_next_pending(model)
    
    if next_pending.request_id == request_id:
        # This is the next request ✓
        return True
    else:
        # Not next in line ✗
        return False
```

**This ensures:**
- No queue jumping
- No out-of-order processing
- Strict FIFO within model

### Visualization

```
Flux Queue Timeline:

Arrival Order: A → B → C → D

Queue State Over Time:

t=0:  [A-PENDING, B-PENDING, C-PENDING, D-PENDING]
      Position:  1          2          3          4

t=1:  [A-PROCESSING, B-PENDING, C-PENDING, D-PENDING]
      try_start(B) → False (A is first)
      try_start(C) → False (A is first)
      try_start(D) → False (A is first)

t=15: [A-COMPLETED, B-PENDING, C-PENDING, D-PENDING]
      try_start(B) → True! (B is now first pending)

t=16: [A-COMPLETED, B-PROCESSING, C-PENDING, D-PENDING]
      try_start(C) → False (B is processing)
      try_start(D) → False (B is processing)

t=30: [A-COMPLETED, B-COMPLETED, C-PENDING, D-PENDING]
      try_start(C) → True! (C is now first pending)

t=31: [A-COMPLETED, B-COMPLETED, C-PROCESSING, D-PENDING]

t=45: [A-COMPLETED, B-COMPLETED, C-COMPLETED, D-PENDING]
      try_start(D) → True!

Processing Order: A → B → C → D (Perfect FIFO!)
```

## Concurrency Model

### Single-Threaded Python

**Key Point:** Python asyncio is single-threaded with cooperative multitasking.

**Implications:**
- No traditional race conditions
- No need for mutex/locks
- Boolean flags sufficient for synchronization
- Atomic operations within event loop

### Processing Locks

```python
# Simple boolean flags
self._flux_processing: bool = False
self._sdxl_processing: bool = False
```

**States:**
- `False`: Model is idle, can accept new request
- `True`: Model is busy, must wait

**Thread Safety:**
- Python GIL ensures atomic boolean operations
- Single event loop = no concurrent access
- No explicit locking needed

### Concurrent Processing

**Maximum Concurrency:** 2 (one per model)

```python
# Scenario: Both models processing
_flux_processing = True   # Flux busy with Request A
_sdxl_processing = True   # SDXL busy with Request B

# Both can process at same time
async def process_A():
    # Flux generation
    await flux_worker.generate()

async def process_B():
    # SDXL generation
    await sdxl_worker.generate()

# Both run concurrently in event loop
await asyncio.gather(process_A(), process_B())
```

### Wait Loop Pattern

```python
async def wait_for_turn(request_id, model):
    """Wait until this request can start processing."""
    
    while True:
        # Try to start
        if queue.try_start_processing(request_id, model):
            break  # Our turn!
        
        # Update user on position
        position = queue.get_queue_position(request_id, model)
        if position and position > 1:
            await update_status(f"Position {position}...")
        
        # Wait before trying again
        await asyncio.sleep(2)
```

**Characteristics:**
- Non-blocking (uses asyncio.sleep)
- Periodic checks (every 2 seconds)
- User feedback on position
- Breaks when processing starts

### Scalability Analysis

#### Current Design (Single Instance)

```
Maximum Throughput:
- Flux: 6-12 images/minute
- SDXL: 4-6 images/minute
- Combined: 10-18 images/minute

Bottleneck: Worker API speed, not queue
```

#### Scaling Limitations

**Problem:** In-memory queue doesn't scale across instances

```
Instance 1:
└─ ImageQueue (own state)
   ├─ Flux queue: [A, B]
   └─ SDXL queue: [C]

Instance 2:
└─ ImageQueue (separate state!)
   ├─ Flux queue: [D]
   └─ SDXL queue: [E, F]

Issue: No coordination between instances
```

**Solutions for Horizontal Scaling:**

1. **Redis Queue (Distributed)**
```python
# Shared queue in Redis
redis_queue = RedisQueue()

# All instances use same queue
request_id = redis_queue.add_request(model, prompt)
```

2. **Message Broker (RabbitMQ/Kafka)**
```python
# Producer (any instance)
mq.publish(channel=f"queue_{model}", message=request)

# Consumer (worker instance)
@mq.subscribe(f"queue_{model}")
def process_request(message):
    # Handle generation
```

3. **Sticky Sessions (Load Balancer)**
```
# User always routes to same instance
LoadBalancer → Hash(user_id) → Instance N
```

## State Management

### In-Memory State

```python
# All state stored in memory
_flux_queue: List[ImageRequest]    # ~1KB per request
_sdxl_queue: List[ImageRequest]    # ~1KB per request
_requests: Dict[str, ImageRequest] # ~1KB per entry
```

**Characteristics:**
- ✅ Fast access (O(1) lookup)
- ✅ Simple implementation
- ✅ No external dependencies
- ⚠️ Lost on restart
- ⚠️ Not shared across instances

### State Lifecycle

```
1. Process starts
   └─ Queue initialized empty

2. Requests added
   └─ State grows in memory

3. Requests complete
   └─ Can be cleaned up

4. Process restarts
   └─ All state lost

5. In-progress generations
   └─ Users see timeout/error
```

### Cleanup Strategy

```python
def cleanup_request(self, request_id: str):
    """
    Remove completed/failed request from memory.
    
    Call after image is sent to user.
    """
    if request_id in self._requests:
        request = self._requests[request_id]
        
        # Remove from queue
        if request.model == "flux":
            if request in self._flux_queue:
                self._flux_queue.remove(request)
        elif request.model == "sdxl":
            if request in self._sdxl_queue:
                self._sdxl_queue.remove(request)
        
        # Remove from lookup
        del self._requests[request_id]
```

**When to cleanup:**
- After image sent to user
- After error message sent
- On process shutdown (automatic)

### Memory Footprint

```
Per Request:
- ImageRequest object: ~1KB
- Queue reference: 8 bytes (pointer)
- Dict entry: ~100 bytes

For 100 active requests:
- Total: ~110KB
- Negligible for modern systems
```

## Performance Analysis

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| `add_request()` | O(1) | Append to list + dict insert |
| `try_start_processing()` | O(n) | Scan queue for next pending |
| `get_queue_position()` | O(n) | Count pending before request |
| `mark_completed()` | O(1) | Dict lookup + flag update |
| `mark_failed()` | O(1) | Dict lookup + flag update |
| `cleanup_request()` | O(n) | Remove from list |

Where n = queue length (typically < 100)

### Space Complexity

```
Space: O(r) where r = total requests

Breakdown:
- Queue lists: O(r) references
- Request dict: O(r) entries
- Each request: O(1) fixed size

Total: ~1KB per request
```

### Throughput Analysis

#### Single Request

```
Total Time: 15-25 seconds

Breakdown:
- Queue operations: <1ms
- Enhancement: 3-5s
- Generation: 5-15s (Flux), 10-15s (SDXL)
- Upload: 1-2s

Queue overhead: Negligible (<0.01%)
```

#### Concurrent Requests

```
Scenario: 10 Flux requests queued

Sequential Processing:
- Request 1: 0s-15s    (position 1)
- Request 2: 15s-30s   (position 2)
- Request 3: 30s-45s   (position 3)
- ...
- Request 10: 135s-150s (position 10)

Last user waits: 150 seconds (2.5 minutes)
```

#### With SDXL Concurrent

```
Scenario: 5 Flux + 5 SDXL requests

Flux Queue:  [1,2,3,4,5]
SDXL Queue:  [1,2,3,4,5]

Processing:
- Flux-1 + SDXL-1 process together (0s-15s)
- Flux-2 + SDXL-2 process together (15s-30s)
- ...

Both models finish simultaneously!
No cross-model blocking ✓
```

### Bottleneck Analysis

**Not the Queue:**
- Queue operations: <1ms
- Negligible compared to generation time

**Actual Bottlenecks:**
1. **Worker API Speed:** 5-15 seconds per image
2. **Network Latency:** Upload/download time
3. **LLM Enhancement:** 3-5 seconds per request

**Queue is NOT the limiting factor.**

---

**Next:** [Design Decisions](design-decisions.md) for rationale behind choices
