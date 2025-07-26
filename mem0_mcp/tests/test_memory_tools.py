"""
Unit tests for memory tools
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.tools.memory_tools import (
    AddMemoryTool,
    SearchMemoriesTool,
    GetMemoriesTool,
    GetMemoryByIdTool,
    DeleteMemoryTool,
    BatchDeleteMemoriesTool,
    MemoryToolsExecutor
)
from src.config.settings import MCPConfig
from src.utils.errors import ToolError, ValidationError


class TestAddMemoryTool:
    """Test AddMemoryTool"""
    
    @pytest.fixture
    def tool(self):
        return AddMemoryTool()
    
    def test_tool_info(self, tool):
        """Test tool information"""
        info = tool.get_info()
        
        assert info["name"] == "add_memory"
        assert "Add new memories" in info["description"]
        assert "messages" in info["inputSchema"]["properties"]
        assert "user_id" in info["inputSchema"]["properties"]
    
    def test_validate_arguments_valid(self, tool):
        """Test validation with valid arguments"""
        args = {
            "messages": [{"role": "user", "content": "test message"}],
            "user_id": "test_user"
        }
        
        # Should not raise exception
        tool.validate_arguments(args)
    
    def test_validate_arguments_missing_messages(self, tool):
        """Test validation with missing messages"""
        args = {"user_id": "test_user"}
        
        with pytest.raises(ValidationError):
            tool.validate_arguments(args)
    
    def test_validate_arguments_empty_messages(self, tool):
        """Test validation with empty messages"""
        args = {
            "messages": [],
            "user_id": "test_user"
        }
        
        with pytest.raises(ValidationError):
            tool.validate_arguments(args)
    
    def test_validate_arguments_invalid_message_format(self, tool):
        """Test validation with invalid message format"""
        args = {
            "messages": [{"invalid": "format"}],
            "user_id": "test_user"
        }
        
        with pytest.raises(ValidationError):
            tool.validate_arguments(args)
    
    @pytest.mark.asyncio
    async def test_execute_success(self, tool):
        """Test successful execution"""
        mock_adapter = AsyncMock()
        mock_adapter.add_memory.return_value = {"id": "mem123", "status": "success"}
        
        args = {
            "messages": [{"role": "user", "content": "I love pizza"}],
            "user_id": "test_user",
            "metadata": {"category": "food"}
        }
        
        result = await tool.execute(args, mock_adapter)
        
        mock_adapter.add_memory.assert_called_once_with(
            messages=args["messages"],
            user_id="test_user",
            metadata={"category": "food"}
        )
        assert result == {"id": "mem123", "status": "success"}
    
    @pytest.mark.asyncio
    async def test_execute_api_error(self, tool):
        """Test execution with API error"""
        mock_adapter = AsyncMock()
        mock_adapter.add_memory.side_effect = Exception("API Error")
        
        args = {
            "messages": [{"role": "user", "content": "test"}],
            "user_id": "test_user"
        }
        
        with pytest.raises(ToolError):
            await tool.execute(args, mock_adapter)


class TestSearchMemoriesTool:
    """Test SearchMemoriesTool"""
    
    @pytest.fixture
    def tool(self):
        return SearchMemoriesTool()
    
    def test_tool_info(self, tool):
        """Test tool information"""
        info = tool.get_info()
        
        assert info["name"] == "search_memories"
        assert "Search memories" in info["description"]
        assert "query" in info["inputSchema"]["properties"]
    
    @pytest.mark.asyncio
    async def test_execute_success(self, tool):
        """Test successful search execution"""
        mock_adapter = AsyncMock()
        mock_adapter.search_memories.return_value = {
            "results": [
                {"id": "mem1", "content": "I love coffee", "score": 0.9},
                {"id": "mem2", "content": "Coffee is great", "score": 0.8}
            ]
        }
        
        args = {
            "query": "coffee preferences",
            "user_id": "test_user",
            "limit": 5
        }
        
        result = await tool.execute(args, mock_adapter)
        
        mock_adapter.search_memories.assert_called_once_with(
            query="coffee preferences",
            user_id="test_user",
            limit=5
        )
        assert len(result["results"]) == 2
        assert result["results"][0]["content"] == "I love coffee"


class TestMemoryToolsExecutor:
    """Test MemoryToolsExecutor"""
    
    @pytest.fixture
    def config(self):
        return MCPConfig(
            mem0_base_url="http://test:8000",
            mem0_api_version="v1"
        )
    
    @pytest.fixture
    def executor(self, config):
        return MemoryToolsExecutor(config)
    
    def test_initialization(self, executor):
        """Test executor initialization"""
        assert executor.config.mem0_base_url == "http://test:8000"
        assert len(executor.tools) == 6  # 6 memory tools
        
        tool_names = [tool.get_info()["name"] for tool in executor.tools.values()]
        expected = [
            "add_memory",
            "search_memories", 
            "get_memories",
            "get_memory_by_id",
            "delete_memory",
            "batch_delete_memories"
        ]
        
        for name in expected:
            assert name in tool_names
    
    def test_get_available_tools(self, executor):
        """Test getting available tools list"""
        tools = executor.get_available_tools()
        
        assert len(tools) == 6
        assert all("name" in tool for tool in tools)
        assert all("description" in tool for tool in tools)
        assert all("inputSchema" in tool for tool in tools)
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, executor):
        """Test successful tool execution"""
        with patch.object(executor, '_get_adapter') as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.add_memory.return_value = {"id": "mem123"}
            mock_get_adapter.return_value = mock_adapter
            
            result = await executor.execute_tool(
                "add_memory",
                {
                    "messages": [{"role": "user", "content": "test"}],
                    "user_id": "test_user"
                }
            )
            
            assert result == {"id": "mem123"}
    
    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, executor):
        """Test executing unknown tool"""
        with pytest.raises(ToolError) as exc_info:
            await executor.execute_tool("unknown_tool", {})
        
        assert "Unknown tool" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_tool_validation_error(self, executor):
        """Test tool execution with validation error"""
        with pytest.raises(ToolError):
            await executor.execute_tool(
                "add_memory",
                {"invalid": "arguments"}
            )
    
    @pytest.mark.asyncio
    async def test_initialize(self, executor):
        """Test executor initialization"""
        # Should not raise exception
        await executor.initialize()
        
        # Check that adapter is created
        assert executor._adapter is not None
    
    @patch('src.tools.memory_tools.V1Adapter')
    @patch('src.tools.memory_tools.Mem0HTTPClient')
    def test_get_adapter_v1(self, mock_client, mock_adapter, executor):
        """Test getting V1 adapter"""
        executor.config.mem0_api_version = "v1"
        
        adapter = executor._get_adapter()
        
        mock_client.assert_called_once_with(executor.config)
        mock_adapter.assert_called_once()
    
    @patch('src.tools.memory_tools.V2Adapter')
    @patch('src.tools.memory_tools.Mem0HTTPClient')
    def test_get_adapter_v2(self, mock_client, mock_adapter, executor):
        """Test getting V2 adapter"""
        executor.config.mem0_api_version = "v2"
        
        adapter = executor._get_adapter()
        
        mock_client.assert_called_once_with(executor.config)
        mock_adapter.assert_called_once()
    
    def test_get_adapter_invalid_version(self, executor):
        """Test getting adapter with invalid version"""
        executor.config.mem0_api_version = "v99"
        
        with pytest.raises(ValueError):
            executor._get_adapter()


if __name__ == "__main__":
    pytest.main([__file__])