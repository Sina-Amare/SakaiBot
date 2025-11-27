# Testing Guide

**Last Updated:** 2024-01-15  
**Audience:** Developers  
**Complexity:** Comprehensive

## Table of Contents

- [Testing Philosophy](#testing-philosophy)
- [Test Structure](#test-structure)
- [Unit Tests](#unit-tests)
- [Integration Tests](#integration-tests)
- [Writing Tests](#writing-tests)
- [Running Tests](#running-tests)
- [Coverage](#coverage)

## Testing Philosophy

### Test Pyramid

```
       ╱╲
      ╱  ╲      Integration Tests (4 tests)
     ╱    ╲     Real API calls, slow
    ╱──────╲
   ╱        ╲   Unit Tests (40+ tests)
  ╱          ╲  Mocked dependencies, fast
 ╱____________╲
```

**Focus:** Heavy unit testing, selective integration testing

### Testing Principles

1. **Fast Feedback:** Unit tests run in < 5 seconds
2. **Isolated:** Each test independent
3. **Repeatable:** Same results every time
4. **Readable:** Tests as documentation
5. **Maintainable:** Easy to update

## Test Structure

### Directory Layout

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
│
├── unit/
│   ├── __init__.py
│   ├── test_image_generator.py    # 11 tests
│   ├── test_image_queue.py        # 13 tests
│   ├── test_prompt_enhancer.py    # 7 tests
│   └── test_image_handler.py      # 9 tests
│
└── integration/
    ├── __init__.py
    └── test_image_integration.py  # 4 tests
```

### Test Files

| File | Tests | Purpose | Mocking |
|------|-------|---------|---------|
| `test_image_generator.py` | 11 | HTTP client behavior | httpx responses |
| `test_image_queue.py` | 13 | Queue operations | None (pure logic) |
| `test_prompt_enhancer.py` | 7 | Enhancement logic | AIProcessor |
| `test_image_handler.py` | 9 | Command handling | Multiple components |
| `test_image_integration.py` | 4 | End-to-end flow | None (real APIs) |

## Unit Tests

### test_image_generator.py

**Purpose:** Test HTTP communication with workers

**Key Test Cases:**

1. **Successful Generation**
```python
@pytest.mark.asyncio
async def test_flux_generation_success():
    """Test successful Flux image generation."""
    generator = ImageGenerator()
    
    # Mock HTTP response
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/png"}
        mock_response.content = b'PNG_IMAGE_DATA'
        mock_get.return_value = mock_response
        
        # Test
        success, image_path, error = await generator.generate_with_flux("test prompt")
        
        # Assertions
        assert success is True
        assert image_path is not None
        assert error is None
        assert os.path.exists(image_path)
        
        # Cleanup
        os.remove(image_path)
```

2. **HTTP Error Handling**
```python
@pytest.mark.asyncio
async def test_flux_rate_limit_error():
    """Test rate limit error handling."""
    generator = ImageGenerator()
    
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response
        
        success, image_path, error = await generator.generate_with_flux("prompt")
        
        assert success is False
        assert image_path is None
        assert "rate limit" in error.lower()
```

3. **Network Errors**
```python
@pytest.mark.asyncio
async def test_flux_network_error():
    """Test network error handling."""
    generator = ImageGenerator()
    
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = httpx.NetworkError("Connection failed")
        
        success, image_path, error = await generator.generate_with_flux("prompt")
        
        assert success is False
        assert "network error" in error.lower()
```

4. **Authentication Errors (SDXL)**
```python
@pytest.mark.asyncio
async def test_sdxl_auth_error():
    """Test SDXL authentication failure."""
    generator = ImageGenerator()
    
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        success, image_path, error = await generator.generate_with_sdxl("prompt")
        
        assert success is False
        assert "api key" in error.lower()
```

**All Test Cases:**
- ✅ Flux success
- ✅ SDXL success
- ✅ Flux 429 rate limit
- ✅ SDXL 401 auth error
- ✅ Network timeout
- ✅ Connection error
- ✅ Invalid content type
- ✅ File save success
- ✅ Retry on transient error
- ✅ No retry on client error
- ✅ Client cleanup

### test_image_queue.py

**Purpose:** Test queue state management

**Key Test Cases:**

1. **Add Request**
```python
def test_add_request_flux(image_queue):
    """Test adding Flux request to queue."""
    request_id = image_queue.add_request("flux", "test prompt", user_id=123)
    
    assert request_id is not None
    assert request_id.startswith("img_")
    
    request = image_queue.get_request(request_id)
    assert request.model == "flux"
    assert request.prompt == "test prompt"
    assert request.status == ImageStatus.PENDING
```

2. **Queue Position**
```python
def test_queue_position_tracking():
    """Test queue position calculation."""
    queue = ImageQueue()
    
    id1 = queue.add_request("flux", "prompt1", 1)
    id2 = queue.add_request("flux", "prompt2", 2)
    id3 = queue.add_request("flux", "prompt3", 3)
    
    assert queue.get_queue_position(id1, "flux") == 1
    assert queue.get_queue_position(id2, "flux") == 2
    assert queue.get_queue_position(id3, "flux") == 3
```

3. **Processing Control**
```python
def test_try_start_processing():
    """Test atomic processing start."""
    queue = ImageQueue()
    
    id1 = queue.add_request("flux", "prompt1", 1)
    id2 = queue.add_request("flux", "prompt2", 2)
    
    # First request can start
    assert queue.try_start_processing(id1, "flux") is True
    assert queue.is_flux_processing() is True
    
    # Second request cannot (first is processing)
    assert queue.try_start_processing(id2, "flux") is False
```

4. **Concurrent Models**
```python
def test_concurrent_different_models():
    """Test Flux and SDXL process concurrently."""
    queue = ImageQueue()
    
    flux_id = queue.add_request("flux", "prompt1", 1)
    sdxl_id = queue.add_request("sdxl", "prompt2", 2)
    
    # Both can start simultaneously
    assert queue.try_start_processing(flux_id, "flux") is True
    assert queue.try_start_processing(sdxl_id, "sdxl") is True
    
    assert queue.is_flux_processing() is True
    assert queue.is_sdxl_processing() is True
```

**All Test Cases:**
- ✅ Add Flux request
- ✅ Add SDXL request
- ✅ Separate queues per model
- ✅ Queue position (Flux)
- ✅ Queue position (SDXL)
- ✅ Try start processing (Flux)
- ✅ Try start processing (SDXL)
- ✅ Concurrent different models
- ✅ Mark completed
- ✅ Mark failed
- ✅ Get status
- ✅ Cleanup request
- ✅ Get pending count

### test_prompt_enhancer.py

**Purpose:** Test LLM-based enhancement

**Key Test Cases:**

1. **Successful Enhancement**
```python
@pytest.mark.asyncio
async def test_enhance_prompt_success():
    """Test successful prompt enhancement."""
    mock_processor = MagicMock()
    mock_processor.is_configured = True
    mock_processor.execute_custom_prompt = AsyncMock(
        return_value="Enhanced prompt with details"
    )
    
    enhancer = PromptEnhancer(mock_processor)
    result = await enhancer.enhance_prompt("cat")
    
    assert result == "Enhanced prompt with details"
    mock_processor.execute_custom_prompt.assert_called_once()
```

2. **Fallback on Error**
```python
@pytest.mark.asyncio
async def test_enhance_prompt_fallback_on_error():
    """Test fallback to original on LLM error."""
    mock_processor = MagicMock()
    mock_processor.is_configured = True
    mock_processor.execute_custom_prompt = AsyncMock(
        side_effect=AIProcessorError("API error")
    )
    
    enhancer = PromptEnhancer(mock_processor)
    result = await enhancer.enhance_prompt("cat")
    
    # Should return original
    assert result == "cat"
```

3. **Not Configured**
```python
@pytest.mark.asyncio
async def test_enhance_prompt_not_configured():
    """Test fallback when LLM not configured."""
    mock_processor = MagicMock()
    mock_processor.is_configured = False
    
    enhancer = PromptEnhancer(mock_processor)
    result = await enhancer.enhance_prompt("cat")
    
    # Should return original immediately
    assert result == "cat"
    mock_processor.execute_custom_prompt.assert_not_called()
```

**All Test Cases:**
- ✅ Success with enhancement
- ✅ Fallback on empty response
- ✅ Fallback on AIProcessorError
- ✅ Fallback when not configured
- ✅ Truncate long responses
- ✅ Remove markdown code blocks
- ✅ Fallback on unexpected exception

### test_image_handler.py

**Purpose:** Test Telegram command handling

**Key Test Cases:**

1. **Command Parsing**
```python
def test_parse_image_command_valid():
    """Test parsing valid /image commands."""
    handler = ImageHandler(mock_processor, mock_generator, mock_enhancer)
    
    message = MagicMock()
    message.text = "/image=flux=a beautiful cat"
    
    result = handler._parse_image_command(message)
    
    assert result is not None
    assert result["model"] == "flux"
    assert result["prompt"] == "a beautiful cat"
```

2. **Invalid Commands**
```python
def test_parse_image_command_invalid_format():
    """Test parsing invalid command format."""
    handler = ImageHandler(mock_processor, mock_generator, mock_enhancer)
    
    message = MagicMock()
    message.text = "/image flux cat"  # Wrong separator
    
    result = handler._parse_image_command(message)
    
    assert result is None
```

3. **Full Processing Flow**
```python
@pytest.mark.asyncio
async def test_process_image_command_success():
    """Test complete image generation flow."""
    # Setup mocks
    mock_processor = MagicMock()
    mock_generator = MagicMock()
    mock_enhancer = MagicMock()
    
    # Mock enhancement
    mock_enhancer.enhance_prompt = AsyncMock(return_value="enhanced prompt")
    
    # Mock generation
    mock_generator.generate_with_flux = AsyncMock(
        return_value=(True, "/path/to/image.png", None)
    )
    
    # Clear queue
    from src.ai.image_queue import image_queue
    image_queue._flux_queue.clear()
    image_queue._flux_processing = False
    
    handler = ImageHandler(mock_processor, mock_generator, mock_enhancer)
    
    # Test (simplified)
    # Full test includes message mocking, client mocking, etc.
    # See actual test file for complete implementation
```

**All Test Cases:**
- ✅ Parse valid Flux command
- ✅ Parse valid SDXL command
- ✅ Parse invalid format
- ✅ Parse missing prompt
- ✅ Validate model
- ✅ Validate prompt length
- ✅ Process Flux success
- ✅ Process SDXL success
- ✅ Handle rate limit

## Integration Tests

### test_image_integration.py

**Purpose:** End-to-end tests with real APIs

**Warning:** These tests:
- Make real HTTP calls
- Use real API keys
- Take longer (30+ seconds each)
- May fail if APIs are down

**Key Test Cases:**

1. **Flux End-to-End**
```python
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_flux_generation_end_to_end():
    """Test complete Flux flow with real worker."""
    config = get_settings()
    if not config.flux_worker_url:
        pytest.skip("Flux worker not configured")
    
    generator = ImageGenerator()
    try:
        success, image_path, error = await generator.generate_with_flux(
            "a simple test image of a cat"
        )
        
        if success:
            assert image_path is not None
            assert Path(image_path).exists()
            # Cleanup
            Path(image_path).unlink(missing_ok=True)
        else:
            pytest.skip(f"Flux generation failed: {error}")
    finally:
        await generator.close()
```

2. **SDXL End-to-End**
```python
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_sdxl_generation_end_to_end():
    """Test complete SDXL flow with real worker."""
    config = get_settings()
    if not config.sdxl_worker_url or not config.sdxl_api_key:
        pytest.skip("SDXL not configured")
    
    generator = ImageGenerator()
    try:
        success, image_path, error = await generator.generate_with_sdxl(
            "a simple test image of a dog"
        )
        
        if success:
            assert image_path is not None
            assert Path(image_path).exists()
            Path(image_path).unlink(missing_ok=True)
        else:
            pytest.skip(f"SDXL generation failed: {error}")
    finally:
        await generator.close()
```

**All Test Cases:**
- ✅ Flux end-to-end
- ✅ SDXL end-to-end
- ✅ Prompt enhancement integration
- ✅ Full flow (enhancement + generation)

**Running Integration Tests:**
```bash
# Run only integration tests
pytest tests/integration/ -v -m integration

# Skip integration tests (default for unit testing)
pytest tests/unit/ -v -m "not integration"
```

## Writing Tests

### Test Template

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_function_name():
    """Test description explaining what is tested."""
    # Arrange: Set up test data and mocks
    mock_dependency = MagicMock()
    mock_dependency.method = AsyncMock(return_value="expected")
    
    instance = ClassUnderTest(mock_dependency)
    
    # Act: Execute the code being tested
    result = await instance.method_to_test(input_data)
    
    # Assert: Verify the results
    assert result == expected_result
    mock_dependency.method.assert_called_once_with(expected_args)
```

### Fixtures

**Shared Setup:**
```python
# conftest.py
import pytest
from src.ai.image_queue import image_queue

@pytest.fixture(autouse=True)
def cleanup_queue():
    """Clean queue before each test."""
    yield
    image_queue._flux_queue.clear()
    image_queue._sdxl_queue.clear()
    image_queue._requests.clear()
    image_queue._flux_processing = False
    image_queue._sdxl_processing = False

@pytest.fixture
def mock_generator():
    """Provide mocked ImageGenerator."""
    generator = MagicMock()
    generator.generate_with_flux = AsyncMock(
        return_value=(True, "/path/image.png", None)
    )
    return generator
```

### Mocking Patterns

**Mock HTTP Client:**
```python
with patch('httpx.AsyncClient.get') as mock_get:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'IMAGE_DATA'
    mock_get.return_value = mock_response
    
    # Test code here
```

**Mock Async Function:**
```python
mock_obj.async_method = AsyncMock(return_value="result")
```

**Mock File Operations:**
```python
with patch('pathlib.Path.unlink') as mock_unlink:
    # Test code
    mock_unlink.assert_called_once()
```

### Assertions

**Common Patterns:**
```python
# Equality
assert result == expected

# Truthiness
assert value is True
assert value is not None

# Collections
assert len(items) == 3
assert item in collection

# Exceptions
with pytest.raises(ValueError):
    function_that_should_raise()

# Mock calls
mock.assert_called_once()
mock.assert_called_with(arg1, arg2)
mock.assert_not_called()

# Async mock calls
mock_async.assert_awaited_once()
```

## Running Tests

### Basic Commands

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific file
pytest tests/unit/test_image_queue.py -v

# Run specific test
pytest tests/unit/test_image_queue.py::test_add_request_flux -v

# Run tests matching pattern
pytest -k "queue" -v
```

### With Output

```bash
# Show print statements
pytest -v -s

# Show verbose output
pytest -vv

# Show local variables on failure
pytest -l
```

### Parallel Execution

```bash
# Install plugin
pip install pytest-xdist

# Run in parallel (4 workers)
pytest -n 4 tests/unit/
```

### Stop on First Failure

```bash
pytest -x tests/unit/
```

### Re-run Failed Tests

```bash
# First run
pytest tests/unit/

# Re-run only failures
pytest --lf tests/unit/
```

## Coverage

### Generate Coverage Report

```bash
# Install coverage
pip install pytest-cov

# Run with coverage
pytest tests/unit/ --cov=src.ai --cov=src.telegram.handlers

# Generate HTML report
pytest tests/unit/ --cov=src.ai --cov-report=html

# Open report
open htmlcov/index.html
```

### Coverage Goals

**Current Coverage:**
- `image_generator.py`: ~90%
- `image_queue.py`: ~95%
- `prompt_enhancer.py`: ~90%
- `image_handler.py`: ~85%

**Target:** >80% line coverage for critical paths

### Uncovered Code

Acceptable to not cover:
- Exception handlers for edge cases
- Cleanup code (finally blocks)
- Debug logging statements

---

**Next:** [Adding Models](adding-models.md) for extending functionality
