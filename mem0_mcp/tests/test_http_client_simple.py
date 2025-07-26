"""
Unit tests for HTTP client - Simplified version
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.client.mem0_client import Mem0HTTPClient
from src.config.settings import MCPConfig
from src.utils.errors import TransportError


class TestMem0HTTPClient:
    """Test Mem0HTTPClient"""
    
    @pytest.fixture
    def config(self):
        return MCPConfig(
            mem0_base_url="http://test:8000",
            mem0_api_version="v1",
            request_timeout=30
        )
    
    @pytest.fixture
    def client(self, config):
        return Mem0HTTPClient(config)
    
    def test_initialization(self, client, config):
        """Test client initialization"""
        assert client.config == config
        assert client.base_url == "http://test:8000"
        assert client.timeout == 30.0
        # max_retries is a constant, not an instance attribute
        from src.config.constants import MAX_RETRIES
        assert MAX_RETRIES == 3
    
    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test client cleanup"""
        # Should not raise exception
        await client.close()
    
    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        """Test using client as async context manager"""
        async with Mem0HTTPClient(config) as client:
            assert isinstance(client, Mem0HTTPClient)
        
        # Should have called close automatically
    
    @pytest.mark.asyncio
    async def test_build_url(self, client):
        """Test URL building"""
        # Test building endpoint URL
        url = client._build_url("/test")
        assert url == "http://test:8000/v1/test"
        
        # Test without leading slash in endpoint
        url = client._build_url("test")
        assert url == "http://test:8000/v1/test"
    
    def test_invalid_url(self):
        """Test initialization with invalid URL"""
        # This test doesn't work because MCPConfig validates the URL first
        # Let's test that MCPConfig validation works
        with pytest.raises(ValueError, match="Invalid Mem0 base URL"):
            MCPConfig(mem0_base_url="invalid-url")


if __name__ == "__main__":
    pytest.main([__file__])