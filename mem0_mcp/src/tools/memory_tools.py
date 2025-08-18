"""
Enhanced memory management tools implementing the hybrid architecture design
"""

import json
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from .base_tool import BaseTool, ToolResult
from ..client.mem0_client import Mem0HTTPClient
from ..client.adapters import V1Adapter, V2Adapter, HybridAdapter, BaseAdapter
from ..config.settings import MCPConfig
from ..protocol.jsonrpc import JSONRPCHandler, JSONRPCResponse
from ..protocol.message_types import ToolsCallResponse
from ..utils.errors import ToolExecutionError
from ..utils.validators import (
    validate_memory_params,
    validate_search_params,
    validate_required_fields
)
from ..utils.logger import get_logger
from .strategies import (
    BaseStrategy,
    StandardStrategy,
    ContextualAddV2Strategy,
    MultimodalStrategy,
    GraphMemoryStrategy,
    AdvancedRetrievalStrategy,
    GraphSearchStrategy
)

logger = get_logger(__name__)


class AddMemoryTool(BaseTool):
    """Tool for adding memories from conversation messages"""

    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="add_memory",
            description="Enhanced tool for adding memories with contextual processing, multimodal support, graph memory, and custom categories"
        )
        self.adapter = adapter

    def get_input_schema(self) -> Dict[str, Any]:
        """Define the input schema for add_memory tool"""
        return {
            "type": "object",
            "required": ["messages"],
            "properties": {
                "messages": {
                    "type": "array",
                    "description": "List of conversation messages to add to memory",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "required": ["role", "content"]
                    }
                },
                "user_id": {
                    "type": "string",
                    "description": "Unique identifier for the user"
                },
                "version": {
                    "type": "string",
                    "description": "API version ('v1' or 'v2' for contextual processing)"
                },
                "enable_graph": {
                    "type": "boolean",
                    "description": "Enable graph memory processing for entity and relationship extraction"
                },
                "output_format": {
                    "type": "string",
                    "description": "Output format for graph memory responses"
                },
                "multimodal_content": {
                    "type": "object",
                    "description": "Multimodal content configuration"
                },
                "custom_categories": {
                    "type": "array",
                    "description": "Custom categorization rules"
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata for the memory"
                },
                "infer": {
                    "type": "boolean",
                    "description": "Whether to infer additional information from the content"
                }
            }
        }

    def _select_strategy(self, arguments: Dict[str, Any]) -> BaseStrategy:
        """
        Select appropriate strategy based on arguments

        Args:
            arguments: Dictionary containing operation parameters

        Returns:
            Selected strategy instance
        """
        # Check for Contextual Add v2
        if arguments.get("version") == "v2":
            logger.debug("Selected ContextualAddV2Strategy based on version=v2")
            return ContextualAddV2Strategy()

        # Check for Graph Memory
        if arguments.get("enable_graph"):
            logger.debug("Selected GraphMemoryStrategy based on enable_graph=True")
            return GraphMemoryStrategy()

        # Check for Multimodal Support
        messages = arguments.get("messages", [])
        if self._has_multimodal_content(messages):
            logger.debug("Selected MultimodalStrategy based on multimodal content detection")
            return MultimodalStrategy()

        # Default to standard strategy
        logger.debug("Selected StandardStrategy as default")
        return StandardStrategy()

    def _has_multimodal_content(self, messages: List[Dict[str, Any]]) -> bool:
        """
        Check if messages contain multimodal content

        Args:
            messages: List of message dictionaries

        Returns:
            True if multimodal content is detected
        """
        multimodal_types = ["image_url", "mdx_url", "pdf_url"]

        for message in messages:
            content = message.get("content")
            if isinstance(content, dict) and "type" in content:
                if content.get("type") in multimodal_types:
                    return True

        return False

    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute add_memory operation with strategy pattern"""
        try:
            # Get user identity
            user_id = self.get_primary_user_id(arguments)

            # Validate required fields
            validate_required_fields(arguments, ["messages"])

            # Add user_id to arguments if not present
            if "user_id" not in arguments:
                arguments["user_id"] = user_id

            # Select and execute strategy
            strategy = self._select_strategy(arguments)
            logger.info(f"Executing add_memory with strategy: {strategy.name}")

            result = await strategy.execute(arguments, self.adapter)

            return ToolResult.success(
                "Memory added successfully",
                structured_content=result
            )

        except Exception as e:
            logger.error(f"Add_memory execution error: {e}")
            return ToolResult.error(f"Memory addition failed: {str(e)}")


class SearchMemoriesTool(BaseTool):
    """Tool for searching memories with advanced retrieval and filtering"""

    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="search_memories",
            description="Enhanced tool for searching memories with advanced retrieval, filtering, and graph memory support"
        )
        self.adapter = adapter

    def get_input_schema(self) -> Dict[str, Any]:
        """Define the input schema for search_memories tool"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant memories"
                },
                "user_id": {
                    "type": "string",
                    "description": "Unique identifier for the user"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 5
                },
                "enable_graph": {
                    "type": "boolean",
                    "description": "Enable graph memory search with entity and relationship queries"
                },
                "filter_memories": {
                    "type": "boolean",
                    "description": "Enable advanced memory filtering"
                },
                "filters": {
                    "type": "object",
                    "description": "Additional filters for memory search"
                },
                "keyword_search": {
                    "type": "boolean",
                    "description": "Enable keyword-based search in addition to semantic search"
                },
                "keyword_weight": {
                    "type": "number",
                    "description": "Weight for keyword search (0-1)",
                    "minimum": 0,
                    "maximum": 1
                },
                "metadata_filters": {
                    "type": "object",
                    "description": "Filter memories by metadata fields"
                },
                "output_format": {
                    "type": "string",
                    "description": "Output format for graph memory responses"
                },
                "rerank": {
                    "type": "boolean",
                    "description": "Enable result reranking for improved relevance"
                },
                "semantic_weight": {
                    "type": "number",
                    "description": "Weight for semantic search (0-1)",
                    "minimum": 0,
                    "maximum": 1
                },
                "time_range": {
                    "type": "object",
                    "description": "Filter memories by time range"
                }
            }
        }

    def _select_search_strategy(self, arguments: Dict[str, Any]) -> BaseStrategy:
        """
        Select appropriate search strategy based on arguments

        Args:
            arguments: Dictionary containing search parameters

        Returns:
            Selected search strategy instance
        """
        # Check for Graph Search
        if arguments.get("enable_graph"):
            logger.debug("Selected GraphSearchStrategy based on enable_graph=True")
            return GraphSearchStrategy()

        # Check for Advanced Retrieval
        advanced_flags = ["keyword_search", "rerank", "filter_memories"]
        if any(arguments.get(flag) for flag in advanced_flags):
            logger.debug("Selected AdvancedRetrievalStrategy based on advanced retrieval flags")
            return AdvancedRetrievalStrategy()

        # Default to standard strategy
        logger.debug("Selected StandardStrategy as default for search")
        return StandardStrategy()

    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute search_memories operation with strategy pattern"""
        try:
            # Get user identity
            user_id = self.get_primary_user_id(arguments)

            # Validate required fields
            if not arguments.get("query"):
                return ToolResult.error("Query parameter is required for search operations")

            # Add user_id to arguments if not present
            if "user_id" not in arguments:
                arguments["user_id"] = user_id

            # Select and execute search strategy
            strategy = self._select_search_strategy(arguments)
            logger.info(f"Executing search_memories with strategy: {strategy.name}")

            result = await strategy.execute(arguments, self.adapter)

            return ToolResult.success(
                "Memory search completed",
                structured_content=result
            )

        except Exception as e:
            logger.error(f"Search_memories execution error: {e}")
            return ToolResult.error(f"Memory search failed: {str(e)}")






class GetMemoriesTool(BaseTool):
    """Tool for retrieving memories"""
    
    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="get_memories",
            description="Get memories for a user"
        )
        self.adapter = adapter
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define the input schema for get_memories tool"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Unique identifier for the user"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of memories to return",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10
                }
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute get_memories tool"""
        try:
            response = await self.adapter.get_memories(**arguments)
            
            if response.get("status") == "success":
                memories = response.get("results", [])
                return ToolResult.success(
                    f"Retrieved {len(memories)} memories",
                    structured_content=response
                )
            else:
                error_msg = response.get("message", "Unknown error occurred")
                return ToolResult.error(f"Failed to get memories: {error_msg}")
                
        except Exception as e:
            logger.error(f"Get_memories execution error: {e}")
            return ToolResult.error(f"Memory retrieval failed: {str(e)}")


class GetMemoryByIdTool(BaseTool):
    """Tool for retrieving a specific memory by ID"""
    
    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="get_memory_by_id",
            description="Get a specific memory by its ID"
        )
        self.adapter = adapter
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define the input schema for get_memory_by_id tool"""
        return {
            "type": "object",
            "required": ["memory_id"],
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "Unique identifier for the memory"
                },
                "user_id": {
                    "type": "string",
                    "description": "Unique identifier for the user"
                }
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute get_memory_by_id tool"""
        try:
            response = await self.adapter.get_memory_by_id(**arguments)
            
            if response.get("status") == "success":
                return ToolResult.success(
                    "Memory retrieved successfully",
                    structured_content=response
                )
            else:
                error_msg = response.get("message", "Unknown error occurred")
                return ToolResult.error(f"Failed to get memory: {error_msg}")
                
        except Exception as e:
            logger.error(f"Get_memory_by_id execution error: {e}")
            return ToolResult.error(f"Memory retrieval failed: {str(e)}")


class UpdateMemoryTool(BaseTool):
    """Tool for updating memories"""
    
    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="update_memory",
            description="Update an existing memory"
        )
        self.adapter = adapter
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define the input schema for update_memory tool"""
        return {
            "type": "object",
            "required": ["memory_id", "text"],
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "Unique identifier for the memory to update"
                },
                "text": {
                    "type": "string",
                    "description": "New content for the memory"
                },
                "user_id": {
                    "type": "string",
                    "description": "Unique identifier for the user"
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata for the memory"
                }
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute update_memory tool"""
        try:
            response = await self.adapter.update_memory(**arguments)
            
            if response.get("status") == "success":
                return ToolResult.success(
                    "Memory updated successfully",
                    structured_content=response
                )
            else:
                error_msg = response.get("message", "Unknown error occurred")
                return ToolResult.error(f"Failed to update memory: {error_msg}")
                
        except Exception as e:
            logger.error(f"Update_memory execution error: {e}")
            return ToolResult.error(f"Memory update failed: {str(e)}")


class DeleteMemoryTool(BaseTool):
    """Tool for deleting memories"""
    
    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="delete_memory",
            description="Delete a specific memory"
        )
        self.adapter = adapter
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define the input schema for delete_memory tool"""
        return {
            "type": "object",
            "required": ["memory_id"],
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "Unique identifier for the memory to delete"
                },
                "user_id": {
                    "type": "string",
                    "description": "Unique identifier for the user"
                }
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute delete_memory tool"""
        try:
            response = await self.adapter.delete_memory(**arguments)
            
            if response.get("status") == "success":
                return ToolResult.success(
                    "Memory deleted successfully",
                    structured_content=response
                )
            else:
                error_msg = response.get("message", "Unknown error occurred")
                return ToolResult.error(f"Failed to delete memory: {error_msg}")
                
        except Exception as e:
            logger.error(f"Delete_memory execution error: {e}")
            return ToolResult.error(f"Memory deletion failed: {str(e)}")


class ProjectConfigTool(BaseTool):
    """Tool for managing project-level configurations"""

    def __init__(self, adapter: BaseAdapter):
        super().__init__(
            name="project_config",
            description="Manage project-level configurations including custom categories and custom instructions"
        )
        self.adapter = adapter

    def get_input_schema(self) -> Dict[str, Any]:
        """Define the input schema for project_config tool"""
        return {
            "type": "object",
            "required": ["operation"],
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Operation type",
                    "enum": ["get", "update", "delete", "reset"]
                },
                "config_type": {
                    "type": "string",
                    "description": "Configuration type",
                    "enum": ["custom_categories", "custom_instructions", "all"]
                },
                "custom_categories": {
                    "type": "array",
                    "description": "Custom categories list",
                    "items": {
                        "type": "object",
                        "description": "Category with single key-value pair"
                    }
                },
                "custom_instructions": {
                    "type": "string",
                    "description": "Custom instructions text"
                },
                "project_id": {
                    "type": "string",
                    "description": "Project ID (optional)"
                }
            }
        }

    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute project_config operation"""
        try:
            from .services.project_config_service import get_config_manager

            config_manager = get_config_manager()
            operation = arguments.get("operation")

            if operation == "get":
                config_type = arguments.get("config_type")
                result = config_manager.get_config(config_type)
                return ToolResult.success(
                    "Configuration retrieved successfully",
                    structured_content={"status": "success", "data": result}
                )

            elif operation == "update":
                if "custom_categories" in arguments:
                    result = config_manager.update_custom_categories(arguments["custom_categories"])
                elif "custom_instructions" in arguments:
                    result = config_manager.update_custom_instructions(arguments["custom_instructions"])
                else:
                    return ToolResult.error("No configuration data provided for update")

                return ToolResult.success(
                    "Configuration updated successfully",
                    structured_content={"status": "success", "data": result}
                )

            elif operation == "delete":
                config_type = arguments.get("config_type")
                if not config_type:
                    return ToolResult.error("Config type is required for delete operation")

                result = config_manager.delete_config(config_type)
                return ToolResult.success(
                    "Configuration deleted successfully",
                    structured_content={"status": "success", "data": result}
                )

            elif operation == "reset":
                result = config_manager.reset_config()
                return ToolResult.success(
                    "Configuration reset successfully",
                    structured_content={"status": "success", "data": result}
                )

            else:
                return ToolResult.error(f"Unsupported operation: {operation}")

        except Exception as e:
            logger.error(f"Project_config execution error: {e}")
            return ToolResult.error(f"Project configuration operation failed: {str(e)}")


class MemoryToolsExecutor:
    """Legacy memory tools executor for backward compatibility"""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.handler = JSONRPCHandler()
        
    async def initialize(self):
        """Initialize the executor"""
        logger.info("MemoryToolsExecutor initialized for backward compatibility")
    
    async def cleanup(self):
        """Cleanup the executor"""
        logger.info("MemoryToolsExecutor cleanup completed")
        
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any], request_id: Optional[str] = None) -> JSONRPCResponse:
        """Execute a memory tool (legacy interface)"""
        logger.debug(f"Legacy tool execution: {tool_name} with request_id: {request_id}")

        # This is a placeholder for legacy compatibility
        # The actual tool execution should go through the new tool manager
        from ..protocol.jsonrpc import JSONRPCHandler

        # Return proper JSON-RPC response
        result = ToolsCallResponse(
            content=[{"type": "text", "text": f"Legacy tool {tool_name} called with arguments: {arguments}"}]
        )

        return JSONRPCHandler.create_response(
            result=result.to_dict(),
            id=request_id
        )