"""
Unit tests for HTTP client
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from typing import Dict, Any

from src.client.mem0_client import Mem0HTTPClient
from src.config.settings import MCPConfig
from src.utils.errors import NetworkError, APIError


class TestMem0HTTPClient:
    """Test Mem0HTTPClient"""
    
    @pytest.fixture
    def config(self):
        return MCPConfig(
            mem0_base_url="http://test:8000",
            mem0_api_version="v1"
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
    async def test_make_request_success(self, client):
        """Test successful HTTP request"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": "test"}
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await client._make_request("GET", "/test")
            
            assert result == {"status": "success", "data": "test"}
            mock_client.request.assert_called_once_with(
                "GET",
                "http://test:8000/test",
                json=None,
                params=None,
                timeout=30.0
            )
    
    @pytest.mark.asyncio
    async def test_make_request_with_data(self, client):
        """Test HTTP request with JSON data"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "created"}
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            data = {"key": "value"}
            result = await client._make_request("POST", "/test", data=data)
            
            mock_client.request.assert_called_once_with(
                "POST",
                "http://test:8000/test",
                json=data,
                params=None,
                timeout=30.0
            )
    
    @pytest.mark.asyncio
    async def test_make_request_with_params(self, client):
        """Test HTTP request with query parameters"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            params = {"limit": 10, "offset": 0}
            result = await client._make_request("GET", "/test", params=params)
            
            mock_client.request.assert_called_once_with(
                "GET",
                "http://test:8000/test",
                json=None,
                params=params,
                timeout=30.0
            )
    
    @pytest.mark.asyncio
    async def test_make_request_http_error(self, client):
        """Test HTTP request with HTTP error"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_response.json.return_value = {"error": "Not found"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "/nonexistent")
            
            assert exc_info.value.status_code == 404
            assert "Not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_make_request_network_error(self, client):
        """Test HTTP request with network error"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.request.side_effect = httpx.ConnectError("Connection failed")
            mock_client_class.return_value = mock_client
            
            with pytest.raises(NetworkError):
                await client._make_request("GET", "/test")
    
    @pytest.mark.asyncio
    async def test_make_request_retry_on_network_error(self, client):
        """Test retry logic on network errors"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            
            # First call fails, second succeeds
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_response.raise_for_status = MagicMock()
            
            mock_client.request.side_effect = [
                httpx.ConnectError("Connection failed"),
                mock_response
            ]
            mock_client_class.return_value = mock_client
            
            result = await client._make_request("GET", "/test")
            
            assert result == {"status": "success"}
            assert mock_client.request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_make_request_max_retries_exceeded(self, client):
        """Test max retries exceeded"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.request.side_effect = httpx.ConnectError("Connection failed")
            mock_client_class.return_value = mock_client
            
            with pytest.raises(NetworkError):
                await client._make_request("GET", "/test")
            
            # Should have tried max_retries + 1 times
            assert mock_client.request.call_count == client.max_retries + 1
    
    @pytest.mark.asyncio
    async def test_make_request_timeout(self, client):
        """Test request timeout"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.request.side_effect = httpx.TimeoutException("Request timeout")
            mock_client_class.return_value = mock_client
            
            with pytest.raises(NetworkError):
                await client._make_request("GET", "/test")
    
    @pytest.mark.asyncio
    async def test_make_request_json_decode_error(self, client):
        """Test JSON decode error"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Invalid response"
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            with pytest.raises(APIError) as exc_info:
                await client._make_request("GET", "/test")
            
            assert "Invalid JSON response" in str(exc_info.value)
    
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


if __name__ == "__main__":
    pytest.main([__file__])