"""Unit tests for TelegramUserVerifier."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.telegram.user_verifier import TelegramUserVerifier
from telethon.tl.types import User
from telethon.errors import FloodWaitError, UsernameInvalidError, PeerIdInvalidError


class TestTelegramUserVerifier:
    """Test cases for TelegramUserVerifier class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.verifier = TelegramUserVerifier(self.mock_client)
    
    @pytest.mark.asyncio
    async def test_verify_user_by_id_success(self):
        """Test successful user verification by ID."""
        # Mock user entity
        mock_user = User(
            id=123456789,
            first_name="Test",
            last_name="User",
            username="testuser",
            bot=False,
            verified=False,
            premium=False
        )
        self.mock_client.get_entity = AsyncMock(return_value=mock_user)
        
        result = await self.verifier.verify_user_by_identifier("123456789")
        
        assert result is not None
        assert result['id'] == 123456789
        assert result['display_name'] == "Test User"
        assert result['username'] == "@testuser"
        assert result['first_name'] == "Test"
        assert result['last_name'] == "User"
        assert result['is_bot'] is False
        assert result['is_verified'] is False
        assert result['is_premium'] is False
    
    @pytest.mark.asyncio
    async def test_verify_user_by_username_success(self):
        """Test successful user verification by username."""
        mock_user = User(
            id=987654321,
            first_name="Another",
            last_name="Test",
            username="anothertest",
            bot=False,
            verified=False,
            premium=False
        )
        self.mock_client.get_entity = AsyncMock(return_value=mock_user)
        
        result = await self.verifier.verify_user_by_identifier("@anothertest")
        
        assert result is not None
        assert result['id'] == 987654321
        assert result['username'] == "@anothertest"
    
    @pytest.mark.asyncio
    async def test_verify_user_by_username_without_at_success(self):
        """Test successful user verification by username without @."""
        mock_user = User(
            id=987654321,
            first_name="Another",
            last_name="Test",
            username="anothertest",
            bot=False,
            verified=False,
            premium=False
        )
        self.mock_client.get_entity = AsyncMock(return_value=mock_user)
        
        result = await self.verifier.verify_user_by_identifier("anothertest")
        
        assert result is not None
        assert result['id'] == 987654321
        assert result['username'] == "@anothertest"
    
    @pytest.mark.asyncio
    async def test_verify_user_by_id_not_found(self):
        """Test user verification by ID when user is not found."""
        self.mock_client.get_entity = AsyncMock(side_effect=ValueError("User not found"))
        
        result = await self.verifier.verify_user_by_identifier("99999")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_verify_user_by_username_not_found(self):
        """Test user verification by username when user is not found."""
        self.mock_client.get_entity = AsyncMock(side_effect=ValueError("User not found"))
        
        result = await self.verifier.verify_user_by_identifier("nonexistentuser")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_verify_user_by_id_with_flood_error(self):
        """Test user verification when facing rate limiting."""
        from src.core.exceptions import TelegramError
        # FloodWaitError constructor takes the delay as the first parameter
        self.mock_client.get_entity = AsyncMock(side_effect=FloodWaitError(30))
        
        with pytest.raises(TelegramError) as exc_info:
            await self.verifier.verify_user_by_identifier("123456789")
        
        assert "Rate limited by Telegram API" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_verify_user_by_invalid_identifier(self):
        """Test user verification with invalid identifier."""
        self.mock_client.get_entity = AsyncMock(side_effect=UsernameInvalidError(None))
        
        result = await self.verifier.verify_user_by_identifier("invalid@user")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_verify_user_by_deleted_user(self):
        """Test user verification when user is deleted."""
        mock_user = User(
            id=123456789,
            first_name="Deleted",
            last_name="User",
            username="deleteduser",
            bot=False,
            verified=False,
            premium=False,
            deleted=True  # User is deleted
        )
        self.mock_client.get_entity = AsyncMock(return_value=mock_user)
        
        result = await self.verifier.verify_user_by_identifier("123456789")
        
        # The implementation should return None for deleted users since they are not accessible in Telegram
        assert result is None
    
    @pytest.mark.asyncio
    async def test_batch_verify_users(self):
        """Test batch verification of multiple users."""
        # Mock users
        mock_user1 = User(id=123, first_name="User", last_name="One", username="user1")
        mock_user2 = User(id=456, first_name="User", last_name="Two", username="user2")
        mock_user3 = User(id=789, first_name="User", last_name="Three", username="user3")
        
        async def mock_get_entity(identifier):
            if identifier == 123:
                return mock_user1
            elif identifier == 456:
                return mock_user2
            elif identifier == "user3":
                return mock_user3
            else:
                raise ValueError("User not found")
        
        self.mock_client.get_entity = AsyncMock(side_effect=mock_get_entity)
        
        identifiers = ["123", "456", "user3", "invalid_user"]
        results = await self.verifier.batch_verify_users(identifiers)
        
        assert len(results) == 3  # Only 3 valid users found
        result_ids = [user['id'] for user in results]
        assert 123 in result_ids
        assert 456 in result_ids
        assert 789 in result_ids
