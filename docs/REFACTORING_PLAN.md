# SakaiBot Refactoring Plan

**Created:** December 6, 2025  
**Status:** Ready for implementation  
**Estimated Effort:** 8-12 hours total

---

## Overview

This document outlines a safe, incremental refactoring plan for SakaiBot. The goal is to improve maintainability without breaking existing functionality.

### Current State

- **70 Python files** across 5 modules
- **4 files over 500 lines** (hard to maintain)
- **0 tests** (high regression risk)
- **Tight coupling** (handlers import 10+ modules each)

### Target State

- No file over 300 lines
- 60%+ test coverage on critical paths
- Dependency injection for testability
- DRY provider implementations

---

## Phase 1: Split Large Files

**Risk:** Low  
**Effort:** 2-3 hours  
**Priority:** Do first

### 1.1 Split `ai_handler.py` (812 lines → 5 files)

Create new directory structure:

```
src/telegram/handlers/
├── ai_handler.py          # Router only (~100 lines)
├── prompt_handler.py      # /prompt command
├── translate_handler.py   # /translate command
├── analyze_handler.py     # /analyze command
└── tellme_handler.py      # /tellme command
```

**Step-by-step:**

1. Create `prompt_handler.py`:

   ```python
   # src/telegram/handlers/prompt_handler.py
   """Handler for /prompt command."""

   from .base import BaseHandler

   class PromptHandler(BaseHandler):
       def __init__(self, ai_processor):
           self._ai_processor = ai_processor

       async def handle(self, prompt_text: str, use_thinking: bool = False, use_web_search: bool = False):
           # Move _handle_prompt_command logic here
           pass
   ```

2. Move `_handle_prompt_command` from `ai_handler.py` to `prompt_handler.py`

3. Update `ai_handler.py` to import and delegate:

   ```python
   from .prompt_handler import PromptHandler

   class AIHandler:
       def __init__(self, ai_processor):
           self._prompt_handler = PromptHandler(ai_processor)

       async def process_ai_command(self, command_type, ...):
           if command_type == "prompt":
               return await self._prompt_handler.handle(...)
   ```

4. Repeat for translate, analyze, tellme

5. **Test after each split** — run all commands

### 1.2 Split `prompts.py` (62KB → directory)

Create new directory structure:

```
src/ai/prompts/
├── __init__.py            # Re-exports all prompts
├── analysis.py            # ANALYZE_*, CONVERSATION_ANALYSIS
├── translation.py         # TRANSLATION_*, AUTO_DETECT
├── image.py               # IMAGE_ENHANCEMENT_*
├── system.py              # FORMATTING_GUIDELINES, SCALING
└── voice.py               # VOICE_MESSAGE_SUMMARY
```

**Step-by-step:**

1. Create `src/ai/prompts/` directory

2. Create `src/ai/prompts/__init__.py`:

   ```python
   """Prompt templates for SakaiBot AI operations."""

   from .analysis import (
       ANALYZE_GENERAL_PROMPT,
       ANALYZE_FUN_PROMPT,
       ANALYZE_ROMANCE_PROMPT,
       CONVERSATION_ANALYSIS_PROMPT,
   )
   from .translation import (
       TRANSLATION_AUTO_DETECT_PROMPT,
       TRANSLATION_SOURCE_TARGET_PROMPT,
   )
   # ... other exports
   ```

3. Move prompts to respective files

4. Update imports in other files (use find/replace)

5. Delete old `prompts.py`

### 1.3 Split `gemini.py` (793 lines → 3 files)

```
src/ai/providers/
├── gemini.py              # Core provider (~400 lines)
├── gemini_thinking.py     # Thinking mode logic (~150 lines)
└── gemini_retry.py        # Retry/error handling (~150 lines)
```

---

## Phase 2: Extract Base Provider

**Risk:** Medium  
**Effort:** 2 hours  
**Priority:** After Phase 1

### 2.1 Create Abstract Base Class

```python
# src/ai/providers/base.py
"""Base class for LLM providers."""

from abc import abstractmethod
from ..llm_interface import LLMProvider

class BaseLLMProvider(LLMProvider):
    """Common functionality for all LLM providers."""

    def __init__(self, config):
        self._config = config
        self._logger = get_logger(self.__class__.__name__)

    def _calculate_max_tokens(self, task_type: str) -> int:
        """Calculate token limits based on task type."""
        if task_type in ("analyze", "tellme", "prompt"):
            return 32000
        elif task_type in ("translate", "prompt_enhancer"):
            return 8000
        return 16000

    def _build_system_prompt(self, task_type: str) -> str:
        """Build system prompt with formatting guidelines."""
        # Move common prompt building here
        pass

    @abstractmethod
    async def _call_api(self, prompt: str, config: dict) -> str:
        """Provider-specific API call. Must be implemented."""
        pass
```

### 2.2 Refactor Gemini to Inherit

```python
# src/ai/providers/gemini.py
from .base import BaseLLMProvider

class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider."""

    def __init__(self, config):
        super().__init__(config)
        # Gemini-specific init (key manager, etc.)

    async def _call_api(self, prompt: str, config: dict) -> str:
        # Only Gemini-specific API call logic
        pass
```

### 2.3 Refactor OpenRouter Similarly

```python
# src/ai/providers/openrouter.py
from .base import BaseLLMProvider

class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter provider."""

    async def _call_api(self, prompt: str, config: dict) -> str:
        # Only OpenRouter-specific API call logic
        pass
```

---

## Phase 3: Add Dependency Injection

**Risk:** Medium  
**Effort:** 2 hours  
**Priority:** After Phase 2

### 3.1 Create Service Container

```python
# src/core/container.py
"""Dependency injection container."""

from dataclasses import dataclass
from typing import Optional

@dataclass
class ServiceContainer:
    """Holds all injectable services."""

    ai_processor: "AIProcessor"
    message_sender: "MessageSender"
    rate_limiter: "RateLimiter"
    error_handler: "ErrorHandler"
    metrics: "MetricsCollector"

    @classmethod
    def create(cls, config: "Config") -> "ServiceContainer":
        """Create container with all services configured."""
        from ..ai.processor import AIProcessor
        from ..utils.message_sender import MessageSender
        from ..utils.rate_limiter import get_ai_rate_limiter
        from ..utils.error_handler import ErrorHandler
        from ..utils.metrics import get_metrics_collector

        return cls(
            ai_processor=AIProcessor(config),
            message_sender=MessageSender(),
            rate_limiter=get_ai_rate_limiter(),
            error_handler=ErrorHandler(),
            metrics=get_metrics_collector(),
        )
```

### 3.2 Update Handlers to Accept Container

```python
# Before
class AIHandler:
    def __init__(self, ai_processor):
        self._ai_processor = ai_processor
        self._message_sender = MessageSender()  # Hidden!
        self._rate_limiter = get_ai_rate_limiter()  # Hidden!

# After
class AIHandler:
    def __init__(self, container: ServiceContainer):
        self._ai_processor = container.ai_processor
        self._message_sender = container.message_sender
        self._rate_limiter = container.rate_limiter
```

### 3.3 Update main.py

```python
# src/main.py
from .core.container import ServiceContainer

class SakaiBot:
    def __init__(self, config: Config):
        self._container = ServiceContainer.create(config)

        self._event_handlers = EventHandlers(
            container=self._container,
            ffmpeg_path=config.ffmpeg_path_resolved
        )
```

---

## Phase 4: Add Tests

**Risk:** None  
**Effort:** 3-4 hours  
**Priority:** Can do anytime

### 4.1 Setup Test Infrastructure

```bash
# Install test dependencies (already in requirements)
pip install pytest pytest-asyncio pytest-cov
```

Create `tests/conftest.py`:

```python
"""Shared test fixtures."""

import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_config():
    """Mock configuration for tests."""
    config = Mock()
    config.gemini_api_keys = ["test-key-1", "test-key-2"]
    config.gemini_model_pro = "gemini-2.5-pro"
    config.gemini_model_flash = "gemini-2.5-flash"
    return config

@pytest.fixture
def mock_ai_processor(mock_config):
    """Mock AI processor."""
    processor = Mock()
    processor.execute_custom_prompt = AsyncMock(return_value="Test response")
    return processor
```

### 4.2 Critical Tests to Write

```
tests/
├── conftest.py
├── unit/
│   ├── test_api_key_manager.py    # Key rotation logic
│   ├── test_rtl_fixer.py          # RTL text handling
│   ├── test_validators.py         # Input validation
│   └── test_response_metadata.py  # Response building
├── integration/
│   ├── test_gemini_provider.py    # API integration
│   ├── test_prompt_handler.py     # Command handling
│   └── test_tts_flow.py           # TTS pipeline
└── __init__.py
```

### 4.3 Example Test

```python
# tests/unit/test_api_key_manager.py
"""Tests for API key rotation."""

import pytest
from src.ai.api_key_manager import GeminiKeyManager, KeyStatus

class TestGeminiKeyManager:
    def test_init_with_multiple_keys(self):
        manager = GeminiKeyManager(["key1", "key2", "key3"])
        assert manager.num_keys == 3
        assert manager.current_key == "key1"

    def test_rotate_to_next_key(self):
        manager = GeminiKeyManager(["key1", "key2"])
        manager.mark_key_rate_limited()
        next_key = manager.rotate_to_next()
        assert next_key == "key2"

    def test_all_keys_exhausted(self):
        manager = GeminiKeyManager(["key1"])
        manager.mark_key_exhausted_for_day()
        assert manager.all_keys_exhausted() == True
```

### 4.4 Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_api_key_manager.py -v
```

---

## Post-Refactoring Checklist

After completing all phases:

- [ ] All files under 300 lines
- [ ] No circular imports
- [ ] All commands work: `/prompt`, `/translate`, `/analyze`, `/tellme`, `/image`, `/tts`, `/stt`
- [ ] Tests pass: `pytest tests/ -v`
- [ ] Coverage > 60%: `pytest --cov=src`

---

## Safety Guidelines

### Before Each Change

1. Create feature branch: `git checkout -b refactor/phase-X`
2. Write test for existing behavior (if possible)
3. Commit working state

### During Each Change

1. Make ONE change at a time
2. Run bot after each change
3. Commit after each working state

### After Each Phase

1. Run full test suite
2. Test all commands manually
3. Merge to main: `git merge --no-ff refactor/phase-X`

---

## Timeline Estimate

| Phase                         | Effort         | Dependencies   |
| ----------------------------- | -------------- | -------------- |
| Phase 1: Split files          | 2-3 hours      | None           |
| Phase 2: Base provider        | 2 hours        | Phase 1        |
| Phase 3: Dependency injection | 2 hours        | Phase 2        |
| Phase 4: Tests                | 3-4 hours      | Can do anytime |
| **Total**                     | **9-11 hours** | -              |

---

## Questions?

If you encounter issues during refactoring, common problems include:

1. **Import errors** — Check relative import paths after moving files
2. **Circular imports** — Use late imports or restructure
3. **Missing dependencies** — Ensure DI container provides all needed services
4. **Test failures** — Check mock configurations match real interfaces
