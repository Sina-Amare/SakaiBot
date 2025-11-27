"""Tests for /help command."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from telethon import events

from src.telegram.commands.self_commands import handle_help_command


@pytest.fixture
def mock_event():
    """Create a mock Telegram event."""
    event = Mock(spec=events.NewMessage.Event)
    event.edit = AsyncMock()
    return event


@pytest.mark.asyncio
async def test_help_main_guide(mock_event):
    """Test main help guide (no args)."""
    await handle_help_command(mock_event, "")
    
    # Verify message was sent
    mock_event.edit.assert_called_once()
    message = mock_event.edit.call_args[0][0]
    
    # Check key sections are present
    assert "SakaiBot - Complete Guide" in message
    assert "IMAGE GENERATION" in message
    assert "AI COMMANDS" in message
    assert "VOICE & AUDIO" in message
    assert "USERBOT COMMANDS" in message
    assert "LIMITATIONS & NOTES" in message
    
    # Check key commands are documented
    assert "/image=flux" in message
    assert "/image=sdxl" in message
    assert "/prompt=" in message
    assert "/translate=" in message
    assert "/analyze=" in message
    assert "/tellme=" in message
    assert "/tts=" in message
    assert "/stt" in message
    assert "/auth" in message
    assert "/status" in message
    
    # Check rate limit mentioned
    assert "10 requests per 60 seconds" in message or "10 req/60s" in message
    
    # Check parse mode is HTML
    assert mock_event.edit.call_args[1]['parse_mode'] == 'html'


@pytest.mark.asyncio
async def test_help_images_guide(mock_event):
    """Test image generation help."""
    await handle_help_command(mock_event, "images")
    
    mock_event.edit.assert_called_once()
    message = mock_event.edit.call_args[0][0]
    
    # Check image-specific content
    assert "Image Generation Guide" in message
    assert "FLUX" in message
    assert "SDXL" in message
    assert "Prompt Tips" in message
    assert "Rate Limits" in message
    assert "Troubleshooting" in message


@pytest.mark.asyncio
async def test_help_image_singular(mock_event):
    """Test 'image' (singular) also works."""
    await handle_help_command(mock_event, "image")
    
    mock_event.edit.assert_called_once()
    message = mock_event.edit.call_args[0][0]
    
    assert "Image Generation Guide" in message


@pytest.mark.asyncio
async def test_help_ai_guide(mock_event):
    """Test AI commands help."""
    await handle_help_command(mock_event, "ai")
    
    mock_event.edit.assert_called_once()
    message = mock_event.edit.call_args[0][0]
    
    # Check AI-specific content
    assert "AI Commands Guide" in message
    assert "PROMPT" in message
    assert "TRANSLATE" in message
    assert "ANALYZE" in message
    assert "TELLME" in message
    assert "10,000 messages" in message


@pytest.mark.asyncio
async def test_help_voice_guide(mock_event):
    """Test voice features help."""
    await handle_help_command(mock_event, "voice")
    
    mock_event.edit.assert_called_once()
    message = mock_event.edit.call_args[0][0]
    
    # Check voice-specific content
    assert "Voice & Audio Guide" in message
    assert "TEXT-TO-SPEECH" in message
    assert "SPEECH-TO-TEXT" in message
    assert "/tts" in message
    assert "/stt" in message
    assert "Auto-Transcription" in message


@pytest.mark.asyncio
async def test_help_auth_guide(mock_event):
    """Test authorization help."""
    await handle_help_command(mock_event, "auth")
    
    mock_event.edit.assert_called_once()
    message = mock_event.edit.call_args[0][0]
    
    # Check auth-specific content
    assert "Authorization Commands" in message
    assert "LIST USERS" in message
    assert "ADD USER" in message
    assert "REMOVE USER" in message
    assert "/auth list" in message
    assert "/auth add" in message
    assert "/auth remove" in message


@pytest.mark.asyncio
async def test_help_unknown_topic(mock_event):
    """Test help with unknown topic."""
    await handle_help_command(mock_event, "unknown_topic")
    
    mock_event.edit.assert_called_once()
    message = mock_event.edit.call_args[0][0]
    
    # Check error message
    assert "Unknown help topic" in message
    assert "unknown_topic" in message
    assert "Available help topics" in message
    assert "/help images" in message
    assert "/help ai" in message


@pytest.mark.asyncio
async def test_help_handles_exceptions(mock_event):
    """Test error handling in help command."""
    # Make edit raise an exception on first call, succeed on error message
    mock_event.edit.side_effect = [Exception("Test error"), None]
    
    # Should not raise, but log error
    with patch('src.telegram.commands.self_commands.logger') as mock_logger:
        await handle_help_command(mock_event, "")
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        assert "Error in /help command" in mock_logger.error.call_args[0][0]
        
        # Verify error message was sent to user
        assert mock_event.edit.call_count == 2
        error_message = mock_event.edit.call_args[0][0]
        assert "❌ Error:" in error_message


@pytest.mark.asyncio
async def test_help_message_not_too_long(mock_event):
    """Test that help messages fit in Telegram's limits."""
    # Telegram message limit is 4096 characters
    MAX_MESSAGE_LENGTH = 4096
    
    test_cases = ["", "images", "ai", "voice", "auth"]
    
    for args in test_cases:
        mock_event.reset_mock()
        await handle_help_command(mock_event, args)
        
        message = mock_event.edit.call_args[0][0]
        assert len(message) < MAX_MESSAGE_LENGTH, f"Help message for '{args}' is too long: {len(message)} chars"


@pytest.mark.asyncio
async def test_help_uses_html_parse_mode(mock_event):
    """Test that all help messages use HTML parse mode."""
    test_cases = ["", "images", "ai", "voice", "auth", "unknown"]
    
    for args in test_cases:
        mock_event.reset_mock()
        await handle_help_command(mock_event, args)
        
        # Check parse_mode argument
        assert mock_event.edit.call_args[1]['parse_mode'] == 'html'


@pytest.mark.asyncio
async def test_help_contains_all_key_features(mock_event):
    """Test that main help mentions all major features."""
    await handle_help_command(mock_event, "")
    
    message = mock_event.edit.call_args[0][0]
    
    # All major features should be mentioned
    features = [
        "/image=flux",
        "/image=sdxl",
        "/prompt=",
        "/translate=",
        "/analyze=",
        "/tellme=",
        "/tts=",
        "/stt",
        "/auth",
        "/status",
    ]
    
    for feature in features:
        assert feature in message, f"Feature '{feature}' not found in main help"


@pytest.mark.asyncio  
async def test_help_provides_clear_navigation(mock_event):
    """Test that help provides clear navigation to subtopics."""
    await handle_help_command(mock_event, "")
    
    message = mock_event.edit.call_args[0][0]
    
    # Should mention subtopic commands
    assert "/help images" in message
    assert "/help ai" in message
    assert "/help voice" in message
