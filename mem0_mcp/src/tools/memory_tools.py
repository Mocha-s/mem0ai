"""
Memory management tools for Mem0 MCP server
"""

import json
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool, ToolResult
from ..client.mem0_client import Mem0HTTPClient
from ..client.adapters import V1Adapter, V2Adapter, BaseAdapter
from ..config.settings import MCPConfig
from ..protocol.jsonrpc import JSONRPCHandler, JSONRPCResponse
from ..protocol.message_types import ToolsCallResponse
from ..utils.errors import ToolExecutionError
from ..utils.validators import (
    validate_memory_params,
    validate_search_params,
    validate_memory_id,
    validate_batch_delete_params,
    validate_required_fields
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AddMemoryTool(BaseTool):
    """Tool for adding memories from messages"""
    
    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="add_memory",
            description="Add new memories from messages"
        )
        self.adapter = adapter
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute add_memory tool"""
        try:
            await self.validate_arguments(arguments)
            
            # Extract required parameters
            messages = arguments["messages"]
            
            # Get user identity from context or arguments
            identity = self.get_user_identity(arguments)
            
            # Optional parameters
            metadata = arguments.get("metadata", {})
            
            # Build parameters for API call using resolved identity
            params = {}
            if identity.user_id:
                params["user_id"] = identity.user_id
            if identity.agent_id:
                params["agent_id"] = identity.agent_id
            if identity.run_id:
                params["run_id"] = identity.run_id
            if metadata:
                params["metadata"] = metadata
            
            self.logger.debug(f"Adding memory for identity: {identity.get_primary_id()}")
            
            # Call Mem0 API
            response = await self.adapter.add_memory(messages, **params)
            
            # Debug: Print response type and content
            self.logger.debug(f"add_memory response type: {type(response)}")
            self.logger.debug(f"add_memory response: {response}")
            
            # Handle different response formats
            if isinstance(response, list):
                # Response is a list, likely from newer API version
                if len(response) > 0:
                    memory = response[0]
                    result_text = f"Successfully added memory"
                    if isinstance(memory, dict):
                        if "id" in memory:
                            result_text += f" with ID: {memory['id']}"
                        if "memory" in memory or "text" in memory:
                            content = memory.get("memory") or memory.get("text", "")
                            result_text += f"\nMemory content: {content}"
                    
                    content = [
                        {"type": "text", "text": result_text},
                        {"type": "text", "text": f"Full response: {json.dumps(response, indent=2)}"}
                    ]
                    return ToolResult(content=content)
                else:
                    return ToolResult.error("Empty response from Mem0 API")
            
            # Format response for MCP (original dict format)
            elif isinstance(response, dict) and response.get("success"):
                result_text = f"Successfully added memory"
                if "results" in response and response["results"]:
                    memories = response["results"]
                    if isinstance(memories, list) and len(memories) > 0:
                        memory = memories[0]
                        if "id" in memory:
                            result_text += f" with ID: {memory['id']}"
                        if "memory" in memory:
                            result_text += f"\nMemory content: {memory['memory']}"
                
                # Return detailed response
                content = [
                    {"type": "text", "text": result_text},
                    {"type": "text", "text": f"Full response: {json.dumps(response, indent=2)}"}
                ]
                return ToolResult(content=content)
            else:
                error_msg = response.get("error", "Unknown error occurred")
                return ToolResult.error(f"Failed to add memory: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"Error in add_memory: {str(e)}")
            return ToolResult.error(str(e))
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema for add_memory"""
        from ..protocol.message_types import ADD_MEMORY_SCHEMA
        return ADD_MEMORY_SCHEMA


class SearchMemoriesTool(BaseTool):
    """Tool for searching memories"""
    
    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="search_memories",
            description="Search memories using natural language query"
        )
        self.adapter = adapter
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute search_memories tool"""
        try:
            await self.validate_arguments(arguments)
            
            # Extract required parameters
            query = arguments["query"]
            
            # Get user identity from context or arguments
            identity = self.get_user_identity(arguments)
            
            # Optional parameters
            limit = arguments.get("limit")
            filters = arguments.get("filters", {})
            
            # Build parameters for API call using resolved identity
            params = {}
            if identity.user_id:
                params["user_id"] = identity.user_id
            if identity.agent_id:
                params["agent_id"] = identity.agent_id
            if identity.run_id:
                params["run_id"] = identity.run_id
            if limit:
                params["limit"] = limit
            if filters:
                params["filters"] = filters
            
            self.logger.debug(f"Searching memories for identity: {identity.get_primary_id()}")
            
            # Call Mem0 API
            response = await self.adapter.search_memories(query, **params)
            
            # Debug: Print response type and content
            self.logger.debug(f"search_memories response type: {type(response)}")
            self.logger.debug(f"search_memories response: {response}")
            
            # Handle different response formats
            if isinstance(response, list):
                # Response is a list, likely from newer API version
                memories = response
            elif isinstance(response, dict) and (response.get("success") or "results" in response):
                # Original dict format
                memories = response.get("results", [])
            else:
                return ToolResult.error(f"Unexpected response format: {type(response)}")
                
            if memories:
                if not memories:
                    return ToolResult.success("No memories found matching the query.")
                
                # Format memories for display
                result_lines = [f"Found {len(memories)} memories:"]
                
                for i, memory in enumerate(memories[:10], 1):  # Limit to first 10
                    memory_id = memory.get("id", "unknown")
                    memory_content = memory.get("memory", "")
                    score = memory.get("score", "N/A")
                    
                    result_lines.append(f"\n{i}. ID: {memory_id}")
                    result_lines.append(f"   Score: {score}")
                    result_lines.append(f"   Content: {memory_content}")
                
                if len(memories) > 10:
                    result_lines.append(f"\n... and {len(memories) - 10} more memories")
                
                content = [
                    {"type": "text", "text": "\n".join(result_lines)},
                    {"type": "text", "text": f"Full response: {json.dumps(response, indent=2)}"}
                ]
                return ToolResult(content=content)
            else:
                error_msg = response.get("error", "Unknown error occurred")
                return ToolResult.error(f"Failed to search memories: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"Error in search_memories: {str(e)}")
            return ToolResult.error(str(e))
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema for search_memories"""
        from ..protocol.message_types import SEARCH_MEMORIES_SCHEMA
        return SEARCH_MEMORIES_SCHEMA


class GetMemoriesTool(BaseTool):
    """Tool for getting memories"""
    
    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="get_memories",
            description="Get memories for a user, agent, or run"
        )
        self.adapter = adapter
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute get_memories tool"""
        try:
            await self.validate_arguments(arguments)
            
            # Get user identity from context or arguments
            identity = self.get_user_identity(arguments)
            
            # Build parameters for API call using resolved identity
            params = {}
            if identity.user_id:
                params["user_id"] = identity.user_id
            if identity.agent_id:
                params["agent_id"] = identity.agent_id
            if identity.run_id:
                params["run_id"] = identity.run_id
            
            # Add any additional arguments (like limit, filters, etc.)
            for key, value in arguments.items():
                if key not in ["user_id", "agent_id", "run_id"] and value is not None:
                    params[key] = value
            
            self.logger.debug(f"Getting memories for identity: {identity.get_primary_id()}")
            
            # Call Mem0 API
            response = await self.adapter.get_memories(**params)
            
            # Debug: Print response type and content
            self.logger.debug(f"get_memories response type: {type(response)}")
            self.logger.debug(f"get_memories response: {response}")
            
            # Handle direct API response format (based on direct testing)
            if isinstance(response, dict) and "results" in response:
                # V1 API returns {"results": [...], "relations": [...]}
                memories = response["results"]
            elif isinstance(response, list):
                # Direct list of memories
                memories = response
            else:
                return ToolResult.error(f"Failed to get memories: Unknown error occurred")
                
            if not memories:
                return ToolResult.success("No memories found.")
                
            # Format memories for display
            result_lines = [f"Found {len(memories)} memories:"]
            
            for i, memory in enumerate(memories[:10], 1):  # Limit to first 10
                memory_id = memory.get("id", "unknown")
                memory_content = memory.get("memory", "")
                created_at = memory.get("created_at", "unknown")
                
                result_lines.append(f"\n{i}. ID: {memory_id}")
                result_lines.append(f"   Created: {created_at}")
                result_lines.append(f"   Content: {memory_content}")
                
                if len(memories) > 10:
                    result_lines.append(f"\n... and {len(memories) - 10} more memories")
                
                content = [
                    {"type": "text", "text": "\n".join(result_lines)},
                    {"type": "text", "text": f"Full response: {json.dumps(response, indent=2)}"}
                ]
                return ToolResult(content=content)
            else:
                error_msg = response.get("error", "Unknown error occurred")
                return ToolResult.error(f"Failed to get memories: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"Error in get_memories: {str(e)}")
            return ToolResult.error(str(e))
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema for get_memories"""
        from ..protocol.message_types import GET_MEMORIES_SCHEMA
        return GET_MEMORIES_SCHEMA


class GetMemoryByIdTool(BaseTool):
    """Tool for getting a specific memory by ID"""
    
    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="get_memory_by_id",
            description="Get a specific memory by its ID"
        )
        self.adapter = adapter
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute get_memory_by_id tool"""
        try:
            await self.validate_arguments(arguments)
            
            memory_id = arguments["memory_id"]
            
            # Call Mem0 API
            response = await self.adapter.get_memory_by_id(memory_id)
            
            # Handle direct API response format (based on direct testing)
            if isinstance(response, dict) and "id" in response:
                # Direct memory object from API
                memory = response
            elif isinstance(response, dict) and "result" in response:
                # Wrapped response
                memory = response["result"]
            else:
                return ToolResult.error(f"Failed to get memory: Unknown error occurred")
                
            if not memory:
                return ToolResult.error(f"Memory with ID {memory_id} not found")
                
            # Format memory details
            result_lines = [f"Memory Details (ID: {memory_id}):"]
            result_lines.append(f"Content: {memory.get('memory', 'N/A')}")
            result_lines.append(f"User ID: {memory.get('user_id', 'N/A')}")
            result_lines.append(f"Created: {memory.get('created_at', 'N/A')}")
            result_lines.append(f"Updated: {memory.get('updated_at', 'N/A')}")
            
            if memory.get("metadata"):
                result_lines.append(f"Metadata: {json.dumps(memory['metadata'], indent=2)}")
            
            content = [
                {"type": "text", "text": "\n".join(result_lines)},
                {"type": "text", "text": f"Full response: {json.dumps(response, indent=2)}"}
            ]
            return ToolResult(content=content)
                
        except Exception as e:
            self.logger.error(f"Error in get_memory_by_id: {str(e)}")
            return ToolResult.error(str(e))
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema for get_memory_by_id"""
        from ..protocol.message_types import GET_MEMORY_BY_ID_SCHEMA
        return GET_MEMORY_BY_ID_SCHEMA


class DeleteMemoryTool(BaseTool):
    """Tool for deleting a specific memory"""
    
    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="delete_memory",
            description="Delete a specific memory by its ID"
        )
        self.adapter = adapter
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute delete_memory tool"""
        try:
            await self.validate_arguments(arguments)
            
            memory_id = arguments["memory_id"]
            
            # Call Mem0 API
            response = await self.adapter.delete_memory(memory_id)
            
            # Debug: Print response type and content
            self.logger.debug(f"delete_memory response type: {type(response)}")
            self.logger.debug(f"delete_memory response: {response}")
            
            # Handle different response formats
            if isinstance(response, dict):
                if response.get("success"):
                    return ToolResult.success(f"Successfully deleted memory with ID: {memory_id}")
                else:
                    error_msg = response.get("error", "Unknown error occurred")
                    return ToolResult.error(f"Failed to delete memory: {error_msg}")
            elif isinstance(response, bool) and response:
                # Some APIs might return just a boolean
                return ToolResult.success(f"Successfully deleted memory with ID: {memory_id}")
            else:
                return ToolResult.error(f"Unexpected response format: {type(response)}")
                
        except Exception as e:
            self.logger.error(f"Error in delete_memory: {str(e)}")
            return ToolResult.error(str(e))
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema for delete_memory"""
        from ..protocol.message_types import DELETE_MEMORY_SCHEMA
        return DELETE_MEMORY_SCHEMA


class BatchDeleteMemoriesTool(BaseTool):
    """Tool for batch deleting memories"""
    
    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="batch_delete_memories",
            description="Delete all memories for a user, agent, or run"
        )
        self.adapter = adapter
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute batch_delete_memories tool"""
        try:
            await self.validate_arguments(arguments)
            
            # Get user identity from context or arguments
            identity = self.get_user_identity(arguments)
            
            # Build parameters for API call using resolved identity
            params = {}
            if identity.user_id:
                params["user_id"] = identity.user_id
            if identity.agent_id:
                params["agent_id"] = identity.agent_id
            if identity.run_id:
                params["run_id"] = identity.run_id
            
            # Add any additional arguments
            for key, value in arguments.items():
                if key not in ["user_id", "agent_id", "run_id"] and value is not None:
                    params[key] = value
            
            self.logger.debug(f"Batch deleting memories for identity: {identity.get_primary_id()}")
            
            # Call Mem0 API
            response = await self.adapter.batch_delete_memories(**params)
            
            # Debug: Print response type and content
            self.logger.debug(f"batch_delete_memories response type: {type(response)}")
            self.logger.debug(f"batch_delete_memories response: {response}")
            
            # Handle different response formats
            success = False
            if isinstance(response, dict):
                success = response.get("success", False)
                error_msg = response.get("error", "Unknown error occurred")
            elif isinstance(response, bool):
                success = response
                error_msg = "Unknown error occurred"
            else:
                return ToolResult.error(f"Unexpected response format: {type(response)}")
            
            if success:
                identifier_info = []
                if arguments.get("user_id"):
                    identifier_info.append(f"user_id: {arguments['user_id']}")
                if arguments.get("agent_id"):
                    identifier_info.append(f"agent_id: {arguments['agent_id']}")
                if arguments.get("run_id"):
                    identifier_info.append(f"run_id: {arguments['run_id']}")
                
                return ToolResult.success(
                    f"Successfully deleted all memories for {', '.join(identifier_info)}"
                )
            else:
                return ToolResult.error(f"Failed to batch delete memories: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"Error in batch_delete_memories: {str(e)}")
            return ToolResult.error(str(e))
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema for batch_delete_memories"""
        from ..protocol.message_types import BATCH_DELETE_MEMORIES_SCHEMA
        return BATCH_DELETE_MEMORIES_SCHEMA


class UpdateMemoryTool(BaseTool):
    """Tool for updating existing memories"""
    
    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="update_memory",
            description="Update an existing memory by ID"
        )
        self.adapter = adapter
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute update_memory tool"""
        try:
            await self.validate_arguments(arguments)
            
            # Extract required parameters
            memory_id = arguments["memory_id"]
            data = arguments["data"]
            
            self.logger.debug(f"Updating memory {memory_id} with new data: {data[:100]}...")
            
            # Call Mem0 API
            response = await self.adapter.update_memory(memory_id=memory_id, data=data)
            
            # Debug: Print response type and content
            self.logger.debug(f"update_memory response type: {type(response)}")
            self.logger.debug(f"update_memory response: {response}")
            
            # Handle different response formats
            success = False
            message = "Memory updated successfully"
            
            if isinstance(response, dict):
                # Check for success indicators
                success = (
                    response.get("success", False) or
                    "message" in response or
                    "memory_id" in response or
                    "updated" in str(response).lower()
                )
                
                if response.get("message"):
                    message = response["message"]
                elif response.get("memory_id"):
                    message = f"Memory {response['memory_id']} updated successfully"
            elif isinstance(response, bool):
                success = response
            else:
                # If we get any response without error, consider it success
                success = True
            
            if success:
                return ToolResult.success(f"Successfully updated memory {memory_id}: {message}")
            else:
                error_msg = response.get("error", "Unknown error occurred") if isinstance(response, dict) else str(response)
                return ToolResult.error(f"Failed to update memory {memory_id}: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"Error in update_memory: {str(e)}")
            return ToolResult.error(str(e))
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema for update_memory"""
        from ..protocol.message_types import UPDATE_MEMORY_SCHEMA
        return UPDATE_MEMORY_SCHEMA


class MemoryToolsExecutor:
    """
    Executor for memory-related MCP tools
    """
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.client: Optional[Mem0HTTPClient] = None
        self.adapter: Optional[BaseAdapter] = None
        self.tools: Dict[str, BaseTool] = {}
        
        logger.info(f"Initialized MemoryToolsExecutor for {config.mem0_base_url}/{config.mem0_api_version}")
    
    async def initialize(self) -> None:
        """Initialize HTTP client and tools"""
        if self.client is None:
            self.client = Mem0HTTPClient(self.config)
            await self.client.connect()
            
            # Create appropriate adapter
            if self.config.mem0_api_version == "v1":
                self.adapter = V1Adapter(self.client)
            elif self.config.mem0_api_version == "v2":
                self.adapter = V2Adapter(self.client)
            else:
                raise ValueError(f"Unsupported API version: {self.config.mem0_api_version}")
            
            # Initialize tools
            self.tools = {
                "add_memory": AddMemoryTool(self.adapter),
                "search_memories": SearchMemoriesTool(self.adapter),
                "get_memories": GetMemoriesTool(self.adapter),
                "get_memory_by_id": GetMemoryByIdTool(self.adapter),
                "delete_memory": DeleteMemoryTool(self.adapter),
                "update_memory": UpdateMemoryTool(self.adapter),
                "batch_delete_memories": BatchDeleteMemoriesTool(self.adapter)
            }
            
            logger.info(f"Initialized {len(self.tools)} memory tools")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.client:
            await self.client.close()
            self.client = None
            self.adapter = None
            self.tools.clear()
            logger.info("Cleaned up MemoryToolsExecutor")
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any], request_id: str) -> JSONRPCResponse:
        """
        Execute a tool and return JSON-RPC response
        
        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments
            request_id: Request ID for response
            
        Returns:
            JSON-RPC response
        """
        try:
            if tool_name not in self.tools:
                return JSONRPCHandler.create_error_response(
                    -32601,  # Method not found
                    f"Tool '{tool_name}' not found",
                    id=request_id
                )
            
            tool = self.tools[tool_name]
            
            # Ensure initialized
            await self.initialize()
            
            # Execute tool directly
            result = await tool.execute(arguments)
            
            # Convert ToolResult to JSON-RPC response
            response_content = ToolsCallResponse(
                content=result.content,
                isError=result.is_error
            )
            
            return JSONRPCHandler.create_response(
                result=response_content.to_dict(),
                id=request_id
            )
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return JSONRPCHandler.create_error_response(
                -32603,  # Internal error
                f"Error executing tool: {str(e)}",
                id=request_id
            )