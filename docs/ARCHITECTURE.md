# SakaiBot Architecture Documentation

## Project Overview

SakaiBot is a sophisticated Telegram userbot built with a modular, layered architecture that emphasizes separation of concerns, extensibility, and maintainability. The project follows modern Python best practices with async/await patterns, dependency injection, and provider-based abstractions.

## Directory Structure

```
SakaiBot/
├── src/                        # Source code root
│   ├── ai/                     # AI and LLM functionality
│   │   ├── __init__.py
│   │   ├── llm_interface.py   # Abstract LLM provider interface
│   │   ├── processor.py       # Main AI processor with provider management
│   │   ├── providers/         # LLM provider implementations
│   │   │   ├── __init__.py
│   │   │   ├── openrouter.py  # OpenRouter provider
│   │   │   └── gemini.py      # Google Gemini provider
│   │   ├── stt.py             # Speech-to-Text processor
│   │   └── tts.py             # Text-to-Speech processor
│   │
│   ├── cli/                    # Command-line interface
│   │   ├── __init__.py
│   │   ├── handler.py         # Main CLI handler and menu logic
│   │   ├── interface.py       # UI utilities and display functions
│   │   └── state.py           # CLI state management
│   │
│   ├── core/                   # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py          # Pydantic-based configuration
│   │   ├── constants.py       # Application constants
│   │   ├── exceptions.py      # Custom exception classes
│   │   └── settings.py        # User settings management
│   │
│   ├── telegram/               # Telegram integration
│   │   ├── __init__.py
│   │   ├── client.py          # Telegram client management
│   │   ├── handlers.py        # Event handlers for commands
│   │   └── utils.py           # Telegram utility functions
│   │
│   ├── utils/                  # Utility modules
│   │   ├── __init__.py
│   │   ├── cache.py           # Cache management for PVs/groups
│   │   ├── command_parser.py  # Command parsing utilities
│   │   └── logging.py         # Centralized logging configuration
│   │
│   ├── __init__.py
│   └── main.py                # Application entry point
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_llm_providers.py
│   └── test_providers.py
│
├── docs/                       # Documentation
│   ├── FEATURES.md           # Feature documentation
│   ├── ARCHITECTURE.md       # This file
│   └── CLI_GUIDE.md          # CLI usage guide
│
├── cache/                      # Cache storage
│   ├── pv_cache.json
│   └── group_cache.json
│
├── data/                       # Persistent data
│   ├── sakaibot_session.session
│   └── sakaibot_user_settings.json
│
├── logs/                       # Application logs
│   └── monitor_activity.log
│
├── main.py                     # Root entry point
├── .env                        # Environment configuration
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

## Architecture Layers

### 1. Presentation Layer (CLI)

The CLI layer provides the user interface through a text-based menu system.

**Components:**
- `CLIHandler`: Main controller for user interactions
- `CLIInterface`: Display utilities and formatting
- `CLIState`: Application state management

**Key Features:**
- Interactive menu navigation
- Async input handling
- State persistence across sessions
- Real-time status updates

### 2. Business Logic Layer

#### AI Processing Module

**Provider Pattern Implementation:**
```python
# Abstract Interface
class LLMProvider(ABC):
    @abstractmethod
    async def execute_prompt(self, user_prompt: str, ...) -> str
    @abstractmethod
    async def translate_text(self, text: str, ...) -> str
    @abstractmethod
    async def analyze_messages(self, messages: List, ...) -> str

# Concrete Implementations
class OpenRouterProvider(LLMProvider)
class GeminiProvider(LLMProvider)

# Factory Pattern in AIProcessor
class AIProcessor:
    def _initialize_provider(self):
        if provider_type == "openrouter":
            self._provider = OpenRouterProvider(config)
        elif provider_type == "gemini":
            self._provider = GeminiProvider(config)
```

**Benefits:**
- Easy addition of new LLM providers
- Provider-agnostic client code
- Consistent interface across providers
- Runtime provider switching

#### Telegram Integration Module

**Event-Driven Architecture:**
```python
# Event Handler Registration
client.add_event_handler(
    handler_function,
    events.NewMessage(pattern=pattern, from_users=users)
)

# Command Processing Pipeline
1. Event Detection → 2. Command Parsing → 3. Validation
→ 4. Processing → 5. Response Generation → 6. Delivery
```

**Components:**
- `TelegramClientManager`: Connection and authentication
- `EventHandlers`: Command and message processing
- `TelegramUtils`: Helper functions for Telegram operations

### 3. Data Layer

#### Configuration Management

**Pydantic-Based Configuration:**
```python
class Config(BaseSettings):
    # Automatic validation
    telegram_api_id: int = Field(..., gt=0)
    telegram_api_hash: str = Field(..., min_length=10)
    
    # Dynamic provider selection
    llm_provider: str = Field(default="openrouter")
    
    # Runtime validation
    @property
    def is_ai_enabled(self) -> bool:
        return self._validate_provider_config()
```

**Features:**
- Type validation
- Environment variable support
- Default value management
- Runtime configuration validation

#### Cache Management

**Two-Tier Cache System:**
1. **Memory Cache**: Fast access during runtime
2. **File Cache**: Persistence across sessions

```python
# Cache Flow
Request → Check Memory → Check File → Fetch from Telegram → Update Both
```

**Cache Files:**
- `cache/pv_cache.json`: Private chat data
- `cache/group_cache.json`: Group information
- Automatic invalidation and refresh mechanisms

### 4. Infrastructure Layer

#### Logging System

**Centralized Logging:**
```python
# Auto-flush file handler for real-time logs
class AutoFlushFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

# Module-specific loggers
logger = get_logger(__class__.__name__)
```

**Features:**
- Hierarchical logger structure
- Auto-flush for real-time monitoring
- Configurable log levels
- Rotation support

#### Error Handling

**Exception Hierarchy:**
```python
BaseException
├── SakaiBotError
│   ├── ConfigurationError
│   ├── TelegramError
│   ├── AIProcessorError
│   └── CacheError
```

**Error Recovery Strategies:**
- Graceful degradation for API failures
- Retry logic with exponential backoff
- User-friendly error messages
- Comprehensive error logging

## Key Design Patterns

### 1. Provider Pattern
Used for LLM abstraction, allowing easy switching between AI providers.

### 2. Factory Pattern
Used in AIProcessor for dynamic provider instantiation.

### 3. Singleton Pattern
Applied to configuration and cache managers for consistent state.

### 4. Observer Pattern
Telegram event handlers follow observer pattern for message processing.

### 5. Command Pattern
Each command type encapsulated with its own processing logic.

## Async/Await Architecture

### Concurrency Model
```python
# Parallel task execution
tasks = [
    process_command(cmd1),
    process_command(cmd2),
    fetch_cache_data()
]
results = await asyncio.gather(*tasks)
```

### Event Loop Management
- Single event loop per application instance
- Graceful shutdown handling
- Task cancellation on interruption

## Data Flow

### Command Processing Flow
```
User Input → Telegram Server → Event Handler → Command Parser
    ↓
Response ← Response Builder ← AI Processor ← Command Processor
```

### AI Request Flow
```
Command → AIProcessor → Provider Selection → API Call
    ↓
Response ← Response Parsing ← API Response ← Provider
```

## Security Architecture

### Authentication Layers
1. **Telegram Authentication**: Session-based with 2FA support
2. **API Key Management**: Secure storage in environment variables
3. **User Authorization**: Whitelist-based command permissions

### Security Features
- No hardcoded credentials
- Session encryption
- Command validation
- Rate limiting considerations
- Audit logging

## Performance Optimizations

### Caching Strategy
- Lazy loading of resources
- Incremental cache updates
- Memory-efficient data structures

### API Optimization
- Batch message fetching
- Connection pooling
- Async I/O for all external calls

### Resource Management
- Proper cleanup on shutdown
- Memory leak prevention
- File handle management

## Extension Points

### Adding New LLM Providers
1. Implement `LLMProvider` interface
2. Add provider configuration to `Config`
3. Register in `AIProcessor._initialize_provider()`
4. Add provider-specific constants

### Adding New Commands
1. Define command pattern in handlers
2. Implement processing logic
3. Add to command parser
4. Update documentation

### Adding New Features
1. Create module in appropriate package
2. Integrate with existing systems
3. Add configuration if needed
4. Update CLI interface

## Testing Architecture

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: Module interaction testing
- **Provider Tests**: LLM provider validation
- **Mock Testing**: Simulated Telegram responses

### Test Structure
```python
tests/
├── test_llm_providers.py  # Provider functionality
├── test_providers.py       # Provider integration
├── test_config.py         # Configuration validation
└── test_commands.py       # Command processing
```

## Deployment Considerations

### Environment Setup
1. Python 3.10+ requirement
2. Virtual environment isolation
3. Dependency management via requirements.txt
4. FFmpeg for audio processing

### Configuration Management
- Environment-based configuration
- Separate dev/prod settings
- Secure credential storage
- Configuration validation on startup

## Monitoring and Maintenance

### Logging Strategy
- Application logs: `logs/monitor_activity.log`
- Error tracking and alerting
- Performance metrics logging
- User activity auditing

### Health Checks
- API connectivity validation
- Cache integrity verification
- Session validity checking
- Resource usage monitoring

## Future Architecture Enhancements

### Planned Improvements
1. **Microservice Architecture**: Separate AI, Telegram, and CLI services
2. **Message Queue**: Implement queue for command processing
3. **Database Integration**: Replace JSON with proper database
4. **WebSocket Support**: Real-time updates for web interface
5. **Plugin System**: Dynamic feature loading
6. **Distributed Caching**: Redis integration for scalability

### Scalability Considerations
- Horizontal scaling for AI processing
- Load balancing for multiple instances
- Distributed session management
- Cloud deployment readiness

---

For feature documentation, see [FEATURES.md](FEATURES.md). For CLI usage, see [CLI_GUIDE.md](CLI_GUIDE.md).