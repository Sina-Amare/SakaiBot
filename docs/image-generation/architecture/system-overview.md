# System Overview

**Last Updated:** 2024-01-15  
**Audience:** Architects, Senior Developers  
**Complexity:** High-level

## Table of Contents

- [Introduction](#introduction)
- [High-Level Architecture](#high-level-architecture)
- [System Components](#system-components)
- [Integration Points](#integration-points)
- [Technology Stack](#technology-stack)
- [Deployment Architecture](#deployment-architecture)
- [Scalability Considerations](#scalability-considerations)

## Introduction

### Purpose

SakaiBot's image generation system enables users to create AI-generated images from text prompts using Flux and SDXL models hosted on Cloudflare Workers, with automatic prompt enhancement via LLM.

### Key Requirements

**Functional:**
- Generate images from text descriptions
- Support multiple AI models (Flux, SDXL)
- Enhance user prompts automatically
- Queue management for concurrent requests
- Real-time status updates to users

**Non-Functional:**
- Response time: 10-25 seconds average
- Availability: 99% uptime (dependent on workers)
- Scalability: Handle multiple concurrent users
- Reliability: Graceful error handling and retries
- Security: API key protection, input validation

## High-Level Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         SakaiBot System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────┐      ┌──────────────┐      ┌────────────────┐  │
│  │  Telegram  │ ───> │    Image     │ ───> │   Image Queue  │  │
│  │   Client   │      │   Handler    │      │   (FIFO/Model) │  │
│  └────────────┘      └──────────────┘      └────────────────┘  │
│         ↑                    │                       │           │
│         │                    ↓                       ↓           │
│         │            ┌──────────────┐      ┌────────────────┐  │
│         │            │   Prompt     │      │     Image      │  │
│         └─────────── │  Enhancer    │      │   Generator    │  │
│                      └──────────────┘      └────────────────┘  │
│                             │                       │           │
│                             ↓                       ↓           │
│                      ┌──────────────┐      ┌────────────────┐  │
│                      │  LLM Service │      │ Cloudflare     │  │
│                      │ (OpenRouter/ │      │ Workers        │  │
│                      │   Gemini)    │      │ (Flux/SDXL)    │  │
│                      └──────────────┘      └────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Request Flow

```
User → Telegram → ImageHandler → Validation → Queue → Enhancement → Generation → Response
                       ↓              ↓           ↓          ↓            ↓
                  Rate Limit     Input Val   FIFO Queue   LLM API   Worker API
```

### Component Layers

```
┌──────────────────────────────────────┐
│     Presentation Layer               │  Telegram commands, status updates
├──────────────────────────────────────┤
│     Application Layer                │  ImageHandler, command routing
├──────────────────────────────────────┤
│     Business Logic Layer             │  Queue, Enhancement, Generation
├──────────────────────────────────────┤
│     Integration Layer                │  HTTP clients, API wrappers
├──────────────────────────────────────┤
│     External Services                │  LLM APIs, Worker APIs
└──────────────────────────────────────┘
```

## System Components

### Core Components

#### 1. ImageHandler
**Location:** `src/telegram/handlers/image_handler.py`  
**Purpose:** Telegram command interface  
**Responsibilities:**
- Parse `/image=` commands
- Validate user input
- Check rate limits
- Add requests to queue
- Send status updates
- Deliver generated images

**Key Methods:**
- `handle_image_command()` - Entry point
- `process_image_command()` - Async processing
- `_parse_image_command()` - Command parsing
- `_send_image()` - Image delivery

#### 2. ImageQueue
**Location:** `src/ai/image_queue.py`  
**Purpose:** Request queue management  
**Responsibilities:**
- Maintain separate FIFO queues per model
- Track request status
- Coordinate processing
- Prevent concurrent processing per model
- Allow concurrent cross-model processing

**Key Data Structures:**
- `_flux_queue: List[ImageRequest]`
- `_sdxl_queue: List[ImageRequest]`
- `_requests: Dict[str, ImageRequest]`

#### 3. PromptEnhancer
**Location:** `src/ai/prompt_enhancer.py`  
**Purpose:** LLM-based prompt improvement  
**Responsibilities:**
- Call LLM with enhancement prompt
- Clean and validate output
- Fallback to original on failure
- Truncate if too long

**Enhancement Pipeline:**
```
User Prompt → Format → LLM Call → Clean → Validate → Enhanced Prompt
                                    ↓
                                 Fallback on Error
```

#### 4. ImageGenerator
**Location:** `src/ai/image_generator.py`  
**Purpose:** HTTP communication with workers  
**Responsibilities:**
- Manage HTTP client
- Send requests to Flux/SDXL workers
- Handle responses and errors
- Save images to disk
- Retry on transient failures

**Request Types:**
- Flux: GET with query params
- SDXL: POST with JSON and Bearer auth

### Supporting Components

#### Configuration (`src/core/config.py`)
- Worker URLs
- API keys
- Timeouts and limits
- Validation rules

#### Error Handler (`src/utils/error_handler.py`)
- User-friendly error messages
- Error classification
- Retry logic

#### Validators (`src/utils/validators.py`)
- Input sanitization
- Model validation
- Prompt validation

#### Rate Limiter (`src/utils/rate_limiter.py`)
- Per-user rate limiting
- 10 requests per 60 seconds
- Shared across AI features

#### Metrics (`src/utils/metrics.py`)
- Request tracking
- Success/failure rates
- Performance monitoring

## Integration Points

### External Services

#### 1. Cloudflare Workers

**Flux Worker:**
- Endpoint: GET request
- Authentication: None
- Input: URL query parameter
- Output: PNG/JPG binary
- Timeout: 120 seconds

**SDXL Worker:**
- Endpoint: POST request
- Authentication: Bearer token
- Input: JSON body
- Output: PNG/JPG binary
- Timeout: 120 seconds

#### 2. LLM Services

**OpenRouter:**
- Purpose: Prompt enhancement
- Authentication: API key
- Model: Configurable (default: gemini-2.0-flash-exp)
- Timeout: 30 seconds

**Gemini:**
- Purpose: Prompt enhancement (alternative)
- Authentication: API key
- Model: Configurable
- Timeout: 30 seconds

#### 3. Telegram

**Inbound:**
- User commands via Telethon
- Message parsing
- User identification

**Outbound:**
- Status messages (editable)
- Image uploads with captions
- Error notifications

### Internal Integrations

#### AIProcessor
- Existing LLM interface
- Used by PromptEnhancer
- Handles provider abstraction

#### TaskManager
- Async task scheduling
- Used for background processing
- Prevents blocking

#### MessageSender
- Telegram message utilities
- Used by ImageHandler

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.10+ | Core implementation |
| HTTP Client | httpx | Latest | Async HTTP requests |
| Telegram | Telethon | Latest | Telegram userbot |
| Validation | Pydantic | 2.x | Configuration validation |
| Testing | pytest | Latest | Unit/integration tests |

### Key Libraries

```python
# HTTP & Networking
httpx                 # Async HTTP client with retry
urllib.parse          # URL encoding

# Data Structures
dataclasses          # ImageRequest model
enum                 # ImageStatus enum
typing               # Type hints

# Async
asyncio              # Async/await patterns
```

### Infrastructure

```
┌──────────────────────────────────────┐
│  SakaiBot Server (Python)            │
│  ├── Application Code                │
│  ├── Temporary Image Storage         │
│  └── Configuration Files             │
└──────────────────────────────────────┘
          ↓                ↓
┌─────────────────┐  ┌──────────────────┐
│  LLM Service    │  │ Cloudflare Edge  │
│  (OpenRouter/   │  │ Workers          │
│   Gemini)       │  │ (Flux/SDXL)      │
└─────────────────┘  └──────────────────┘
```

## Deployment Architecture

### Single-Instance Deployment

```
┌────────────────────────────────────────────┐
│           Server Instance                  │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │  SakaiBot Process                    │ │
│  │  ├── Telegram Client                 │ │
│  │  ├── Image Generation System         │ │
│  │  ├── Queue (In-Memory)               │ │
│  │  └── Temp Storage (Local Disk)       │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  Network: Outbound HTTPS                   │
│  Storage: temp/images/                     │
│  Config: .env file                         │
└────────────────────────────────────────────┘
```

**Characteristics:**
- ✅ Simple setup
- ✅ Low maintenance
- ✅ Cost-effective
- ⚠️ Single point of failure
- ⚠️ Limited scalability

### State Management

**Stateful Components:**
- Queue: In-memory (per-process)
- Rate limiter: In-memory (per-process)
- Temporary files: Local disk

**Implications:**
- Process restart clears queue
- No cross-instance coordination needed
- Temporary files cleaned up on restart

## Scalability Considerations

### Current Limitations

1. **Single Process Queue**
   - Queue is in-memory, not shared
   - Multiple instances = separate queues
   - No cross-instance coordination

2. **Sequential Processing**
   - One request at a time per model
   - Intentional design for FIFO guarantees
   - Concurrent models supported

3. **Local File Storage**
   - Images saved to local disk
   - Not shared across instances
   - Cleaned up after sending

### Scaling Strategies

#### Vertical Scaling (Recommended)
```
More powerful server → More memory/CPU → Better performance
```

**Benefits:**
- No architecture changes needed
- Simple to implement
- Maintains FIFO guarantees

**Limits:**
- Single instance ceiling
- Eventual hardware limits

#### Horizontal Scaling (Future)

**Option 1: Multiple Independent Instances**
```
Load Balancer → Multiple SakaiBot Instances
                (Each with own queue)
```

**Pros:** Simple, no shared state  
**Cons:** Users may hit different instances

**Option 2: Shared Queue Service**
```
All Instances → Redis Queue → Coordinated Processing
```

**Pros:** True horizontal scaling  
**Cons:** Requires Redis, more complex

### Performance Characteristics

**Throughput:**
- Flux: ~6-12 images/minute per instance
- SDXL: ~4-6 images/minute per instance
- Combined: Can process both simultaneously

**Latency:**
- Queue time: 0-30s (depends on position)
- Enhancement: 3-5s
- Generation: 5-15s (Flux), 10-15s (SDXL)
- Total: 10-55s

**Capacity:**
- Rate limit: 10 req/60s per user
- Queue size: Unlimited (memory-bound)
- Concurrent models: 2 (Flux + SDXL)

### Resource Requirements

**Memory:**
- Base: ~200MB (SakaiBot)
- Per request: ~2-5MB (queue + temp file)
- Peak: ~500MB (with active generation)

**CPU:**
- Minimal (mostly I/O wait)
- Spikes during prompt enhancement (LLM call)

**Disk:**
- Config: <1MB
- Temp images: ~2-10MB per image
- Cleaned up automatically

**Network:**
- Inbound: Minimal (Telegram commands)
- Outbound: ~5-20MB per image (upload to Telegram)
- API calls: ~100KB per request

---

**Next:** [Component Design](component-design.md) for detailed component breakdown
