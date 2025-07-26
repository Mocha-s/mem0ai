"""
Integration tests for Mem0 MCP Server
"""

import asyncio
import json
import pytest
import httpx
from typing import Dict, Any
from unittest.mock import patch, AsyncMock, MagicMock

from src.server import MCPServer, run_server
from src.config.settings import MCPConfig
from src.transport.http_transport import HTTPTransport
from src.protocol.jsonrpc import JSONRPCRequest


class TestMCPServerIntegration:
    """Integration tests for MCP server"""
    
    @pytest.fixture
    def config(self):
        """Test configuration"""
        return MCPConfig(
            host="localhost",
            port=8999,  # Use different port for tests
            mem0_base_url="http://mock-mem0:8000",
            mem0_api_version="v1",
            debug=True
        )
    
    @pytest.fixture
    async def server(self, config):
        """Create and initialize test server"""
        server = MCPServer(config)
        await server.initialize()
        yield server
        await server.stop()
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, server):
        """Test server initialization"""
        assert server.config.port == 8999
        assert server.transport is not None
        assert server.protocol_handler is not None
        assert server.tool_executor is not None
    
    @pytest.mark.asyncio
    async def test_server_health_check(self, server):
        """Test server health check"""
        health = await server.health_check()
        
        assert health["transport"] == "http"
        assert health["mem0_url"] == "http://mock-mem0:8000"
        assert health["api_version"] == "v1"
    
    @pytest.mark.asyncio 
    async def test_message_handling_initialize(self, server):
        """Test MCP initialize message handling"""
        init_message = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            },
            "id": "init-1"
        }
        
        response_json = await server._handle_message(json.dumps(init_message))
        response = json.loads(response_json)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "init-1"
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2025-06-18"
        assert "serverInfo" in response["result"]
    
    @pytest.mark.asyncio
    async def test_message_handling_tools_list(self, server):
        """Test tools/list message handling"""
        tools_message = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": "tools-1"
        }
        
        response_json = await server._handle_message(json.dumps(tools_message))
        response = json.loads(response_json)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "tools-1"
        assert "result" in response
        assert "tools" in response["result"]
        
        tools = response["result"]["tools"]
        assert len(tools) == 6  # 6 memory tools
        
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "add_memory", "search_memories", "get_memories",
            "get_memory_by_id", "delete_memory", "batch_delete_memories"
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_names
    
    @pytest.mark.asyncio
    async def test_message_handling_invalid_json(self, server):
        """Test handling of invalid JSON"""
        response_json = await server._handle_message("invalid json")
        response = json.loads(response_json)
        
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32700  # Parse error
    
    @pytest.mark.asyncio
    async def test_message_handling_invalid_method(self, server):
        """Test handling of invalid method"""
        invalid_message = {
            "jsonrpc": "2.0",
            "method": "invalid_method",
            "params": {},
            "id": "invalid-1"
        }
        
        response_json = await server._handle_message(json.dumps(invalid_message))
        response = json.loads(response_json)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "invalid-1"
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found


class TestHTTPTransportIntegration:
    """Integration tests for HTTP transport"""
    
    @pytest.fixture
    def config(self):
        return MCPConfig(
            host="localhost",
            port=8998,
            mem0_base_url="http://mock-mem0:8000",
            debug=True
        )
    
    @pytest.mark.asyncio
    async def test_http_request_response_cycle(self, config):
        """Test complete HTTP request/response cycle"""
        
        async def mock_message_handler(message: str, session_id: str = None):
            # Parse the message and return a simple response
            try:
                parsed = json.loads(message)
                if parsed.get("method") == "initialize":
                    return json.dumps({
                        "jsonrpc": "2.0",
                        "id": parsed.get("id"),
                        "result": {
                            "protocolVersion": "2025-06-18",
                            "serverInfo": {"name": "test-server", "version": "1.0.0"}
                        }
                    })
            except Exception:
                pass
            return None
        
        # Create transport with mock handler
        transport = HTTPTransport(config, mock_message_handler)
        
        # Start transport in background
        server_task = asyncio.create_task(transport.start())
        
        # Wait a bit for server to start
        await asyncio.sleep(0.1)
        
        try:
            # Make HTTP request to server
            async with httpx.AsyncClient() as client:
                init_message = {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"}
                    },
                    "id": "test-init"
                }
                
                response = await client.post(
                    f"http://localhost:{config.port}/message",
                    json=init_message,
                    timeout=5.0
                )
                
                assert response.status_code == 200
                result = response.json()
                
                assert result["jsonrpc"] == "2.0"
                assert result["id"] == "test-init"
                assert "result" in result
                assert result["result"]["protocolVersion"] == "2025-06-18"
        
        finally:
            # Stop transport
            await transport.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


class TestToolExecutionIntegration:
    """Integration tests for tool execution"""
    
    @pytest.fixture
    def config(self):
        return MCPConfig(
            mem0_base_url="http://mock-mem0:8000",
            mem0_api_version="v1"
        )
    
    @pytest.mark.asyncio
    async def test_add_memory_tool_integration(self, config):
        """Test add_memory tool execution integration"""
        server = MCPServer(config)
        await server.initialize()
        
        # Mock the HTTP client response
        with patch('src.client.mem0_client.Mem0HTTPClient._make_request') as mock_request:
            mock_request.return_value = {
                "id": "mem_123",
                "message": "Memory added successfully",
                "metadata": {"category": "test"}
            }
            
            # Create tool call message
            tool_message = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "add_memory",
                    "arguments": {
                        "messages": [
                            {"role": "user", "content": "I love integration testing"}
                        ],
                        "user_id": "test_user",
                        "metadata": {"category": "test"}
                    }
                },
                "id": "tool-1"
            }
            
            response_json = await server._handle_message(json.dumps(tool_message))
            response = json.loads(response_json)
            
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "tool-1"
            assert "result" in response
            assert response["result"]["content"][0]["text"] == json.dumps({
                "id": "mem_123",
                "message": "Memory added successfully",
                "metadata": {"category": "test"}
            })
            
            # Verify HTTP client was called correctly
            mock_request.assert_called_once_with(
                "POST",
                "/v1/memories/",
                data={
                    "messages": [{"role": "user", "content": "I love integration testing"}],
                    "user_id": "test_user",
                    "metadata": {"category": "test"}
                }
            )
        
        await server.stop()
    
    @pytest.mark.asyncio
    async def test_search_memories_tool_integration(self, config):
        """Test search_memories tool execution integration"""
        server = MCPServer(config)
        await server.initialize()
        
        # Mock the HTTP client response
        with patch('src.client.mem0_client.Mem0HTTPClient._make_request') as mock_request:
            mock_request.return_value = {
                "results": [
                    {
                        "id": "mem_1",
                        "memory": "User loves coffee",
                        "score": 0.95,
                        "metadata": {"category": "preference"}
                    },
                    {
                        "id": "mem_2", 
                        "memory": "User drinks coffee every morning",
                        "score": 0.87,
                        "metadata": {"category": "habit"}
                    }
                ]
            }
            
            # Create tool call message
            tool_message = {
                "jsonrpc": "2.0",
                "method": "tools/call",  
                "params": {
                    "name": "search_memories",
                    "arguments": {
                        "query": "coffee preferences",
                        "user_id": "test_user",
                        "limit": 10
                    }
                },
                "id": "search-1"
            }
            
            response_json = await server._handle_message(json.dumps(tool_message))
            response = json.loads(response_json)
            
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == "search-1"
            assert "result" in response
            
            result_data = json.loads(response["result"]["content"][0]["text"])
            assert "results" in result_data
            assert len(result_data["results"]) == 2
            assert result_data["results"][0]["memory"] == "User loves coffee"
            
            # Verify HTTP client was called correctly
            mock_request.assert_called_once_with(
                "GET",
                "/v1/memories/search/",
                params={
                    "query": "coffee preferences",
                    "user_id": "test_user",
                    "limit": 10
                }
            )
        
        await server.stop()


class TestEndToEndWorkflow:
    """End-to-end workflow tests"""
    
    @pytest.mark.asyncio
    async def test_complete_memory_workflow(self):
        """Test complete memory management workflow"""
        config = MCPConfig(
            host="localhost",
            port=8997,
            mem0_base_url="http://mock-mem0:8000",
            mem0_api_version="v1",
            debug=True
        )
        
        server = MCPServer(config)
        await server.initialize()
        
        # Start server
        transport_task = asyncio.create_task(server.transport.start())
        await asyncio.sleep(0.1)  # Wait for server to start
        
        try:
            async with httpx.AsyncClient() as client:
                base_url = f"http://localhost:{config.port}"
                
                # Step 1: Initialize connection
                init_response = await client.post(f"{base_url}/message", json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"}
                    },
                    "id": "init"
                })
                
                assert init_response.status_code == 200
                init_result = init_response.json()
                assert "result" in init_result
                
                # Step 2: List available tools
                tools_response = await client.post(f"{base_url}/message", json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": "tools"
                })
                
                assert tools_response.status_code == 200
                tools_result = tools_response.json()
                assert len(tools_result["result"]["tools"]) == 6
                
                # Step 3: Mock add memory operation  
                with patch('src.client.mem0_client.Mem0HTTPClient._make_request') as mock_request:
                    mock_request.return_value = {"id": "mem_workflow_123", "status": "success"}
                    
                    add_response = await client.post(f"{base_url}/message", json={
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "add_memory",
                            "arguments": {
                                "messages": [{"role": "user", "content": "Workflow test memory"}],
                                "user_id": "workflow_user"
                            }
                        },
                        "id": "add"
                    })
                    
                    assert add_response.status_code == 200
                    add_result = add_response.json()
                    assert "result" in add_result
                
                # Step 4: Mock search memories
                with patch('src.client.mem0_client.Mem0HTTPClient._make_request') as mock_request:
                    mock_request.return_value = {
                        "results": [{"id": "mem_workflow_123", "memory": "Workflow test memory", "score": 1.0}]
                    }
                    
                    search_response = await client.post(f"{base_url}/message", json={
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "search_memories",
                            "arguments": {
                                "query": "workflow test",
                                "user_id": "workflow_user"
                            }
                        },
                        "id": "search"
                    })
                    
                    assert search_response.status_code == 200
                    search_result = search_response.json()
                    assert "result" in search_result
        
        finally:
            await server.stop()
            transport_task.cancel()
            try:
                await transport_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])