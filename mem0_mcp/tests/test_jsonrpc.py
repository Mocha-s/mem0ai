"""
Unit tests for JSON-RPC protocol handling
"""

import json
import pytest
from typing import Any, Dict

from src.protocol.jsonrpc import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    JSONRPCHandler
)
from src.utils.errors import ProtocolError


class TestJSONRPCRequest:
    """Test JSONRPCRequest class"""
    
    def test_valid_request(self):
        """Test creating valid JSON-RPC request"""
        request = JSONRPCRequest(
            method="test_method",
            params={"arg1": "value1"},
            id="test-id"
        )
        
        assert request.jsonrpc == "2.0"
        assert request.method == "test_method"
        assert request.params == {"arg1": "value1"}
        assert request.id == "test-id"
    
    def test_notification_request(self):
        """Test notification request (no id)"""
        request = JSONRPCRequest(method="notify")
        
        assert request.jsonrpc == "2.0"
        assert request.method == "notify"
        assert request.params is None
        assert request.id is None
    
    def test_to_dict(self):
        """Test converting request to dictionary"""
        request = JSONRPCRequest(
            method="test",
            params={"key": "value"},
            id=123
        )
        
        data = request.to_dict()
        expected = {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"key": "value"},
            "id": 123
        }
        
        assert data == expected
    
    def test_to_json(self):
        """Test converting request to JSON string"""
        request = JSONRPCRequest(method="test", id="abc")
        json_str = request.to_json()
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["method"] == "test"
        assert parsed["id"] == "abc"


class TestJSONRPCResponse:
    """Test JSONRPCResponse class"""
    
    def test_success_response(self):
        """Test success response"""
        response = JSONRPCResponse(
            result={"status": "ok"},
            id="test-id"
        )
        
        assert response.jsonrpc == "2.0"
        assert response.result == {"status": "ok"}
        assert response.error is None
        assert response.id == "test-id"
    
    def test_error_response(self):
        """Test error response"""
        error = JSONRPCError(code=-32000, message="Test error")
        response = JSONRPCResponse(
            error=error,
            id="test-id"
        )
        
        assert response.jsonrpc == "2.0"
        assert response.result is None
        assert response.error == error
        assert response.id == "test-id"
    
    def test_to_dict(self):
        """Test converting response to dictionary"""
        response = JSONRPCResponse(
            result={"data": "test"},
            id=456
        )
        
        data = response.to_dict()
        expected = {
            "jsonrpc": "2.0",
            "result": {"data": "test"},
            "id": 456
        }
        
        assert data == expected


class TestJSONRPCError:
    """Test JSONRPCError class"""
    
    def test_basic_error(self):
        """Test basic error creation"""
        error = JSONRPCError(code=-32600, message="Invalid Request")
        
        assert error.code == -32600
        assert error.message == "Invalid Request"
        assert error.data is None
    
    def test_error_with_data(self):
        """Test error with additional data"""
        error = JSONRPCError(
            code=-32000,
            message="Server error",
            data={"details": "Something went wrong"}
        )
        
        assert error.code == -32000
        assert error.message == "Server error"
        assert error.data == {"details": "Something went wrong"}
    
    def test_to_dict(self):
        """Test converting error to dictionary"""
        error = JSONRPCError(
            code=-32601,
            message="Method not found",
            data="test_method"
        )
        
        data = error.to_dict()
        expected = {
            "code": -32601,
            "message": "Method not found",
            "data": "test_method"
        }
        
        assert data == expected


class TestJSONRPCHandler:
    """Test JSONRPCHandler class"""
    
    def test_parse_valid_request(self):
        """Test parsing valid JSON-RPC request"""
        message = json.dumps({
            "jsonrpc": "2.0",
            "method": "test_method",
            "params": {"arg": "value"},
            "id": "123"
        })
        
        request = JSONRPCHandler.parse_message(message)
        
        assert isinstance(request, JSONRPCRequest)
        assert request.method == "test_method"
        assert request.params == {"arg": "value"}
        assert request.id == "123"
    
    def test_parse_notification(self):
        """Test parsing notification (no id)"""
        message = json.dumps({
            "jsonrpc": "2.0",
            "method": "notify"
        })
        
        request = JSONRPCHandler.parse_message(message)
        
        assert isinstance(request, JSONRPCRequest)
        assert request.method == "notify"
        assert request.id is None
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON"""
        with pytest.raises(ProtocolError) as exc_info:
            JSONRPCHandler.parse_message("invalid json")
        
        assert exc_info.value.code == -32700  # Parse error
    
    def test_parse_missing_jsonrpc(self):
        """Test parsing message missing jsonrpc field"""
        message = json.dumps({
            "method": "test",
            "id": "123"
        })
        
        with pytest.raises(ProtocolError) as exc_info:
            JSONRPCHandler.parse_message(message)
        
        assert exc_info.value.code == -32600  # Invalid Request
    
    def test_parse_invalid_jsonrpc_version(self):
        """Test parsing message with invalid jsonrpc version"""
        message = json.dumps({
            "jsonrpc": "1.0",
            "method": "test",
            "id": "123"
        })
        
        with pytest.raises(ProtocolError) as exc_info:
            JSONRPCHandler.parse_message(message)
        
        assert exc_info.value.code == -32600  # Invalid Request
    
    def test_parse_missing_method(self):
        """Test parsing request missing method"""
        message = json.dumps({
            "jsonrpc": "2.0",
            "id": "123"
        })
        
        with pytest.raises(ProtocolError) as exc_info:
            JSONRPCHandler.parse_message(message)
        
        assert exc_info.value.code == -32600  # Invalid Request
    
    def test_validate_valid_request(self):
        """Test validating valid request"""
        request = JSONRPCRequest(method="test", id="123")
        
        # Should not raise exception
        JSONRPCHandler.validate_request(request)
    
    def test_validate_empty_method(self):
        """Test validating request with empty method"""
        request = JSONRPCRequest(method="", id="123")
        
        with pytest.raises(ProtocolError) as exc_info:
            JSONRPCHandler.validate_request(request)
        
        assert exc_info.value.code == -32600  # Invalid Request
    
    def test_create_success_response(self):
        """Test creating success response"""
        result = {"status": "success"}
        response = JSONRPCHandler.create_success_response(result, "test-id")
        
        assert isinstance(response, JSONRPCResponse)
        assert response.result == result
        assert response.error is None
        assert response.id == "test-id"
    
    def test_create_error_response(self):
        """Test creating error response"""
        response = JSONRPCHandler.create_error_response(
            code=-32000,
            message="Test error",
            data="extra info",
            id="test-id"
        )
        
        assert isinstance(response, JSONRPCResponse)
        assert response.result is None
        assert response.error["code"] == -32000
        assert response.error["message"] == "Test error"
        assert response.error["data"] == "extra info"
        assert response.id == "test-id"
    
    def test_create_error_response_no_id(self):
        """Test creating error response without id"""
        response = JSONRPCHandler.create_error_response(
            code=-32601,
            message="Method not found"
        )
        
        assert response.id is None
        assert response.error["code"] == -32601


if __name__ == "__main__":
    pytest.main([__file__])