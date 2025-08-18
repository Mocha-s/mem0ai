"""
MCP protocol message types and schemas
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


class MCPMessageType(Enum):
    """MCP message types"""
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    PING = "ping"


@dataclass
class MCPMessage:
    """Base MCP message"""
    pass


@dataclass
class ServerInfo:
    """Server information"""
    name: str
    version: str


@dataclass
class ServerCapabilities:
    """Server capabilities declaration"""
    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        capabilities = {}
        
        if self.tools is not None:
            capabilities["tools"] = self.tools
        if self.resources is not None:
            capabilities["resources"] = self.resources  
        if self.prompts is not None:
            capabilities["prompts"] = self.prompts
        if self.logging is not None:
            capabilities["logging"] = self.logging
            
        return capabilities


@dataclass
class ClientCapabilities:
    """Client capabilities declaration"""
    sampling: Optional[Dict[str, Any]] = None
    experimental: Optional[Dict[str, Any]] = None


@dataclass
class InitializeRequest(MCPMessage):
    """Initialize request message"""
    protocolVersion: str
    capabilities: ClientCapabilities
    clientInfo: ServerInfo


@dataclass
class InitializeResponse(MCPMessage):
    """Initialize response message"""
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: ServerInfo
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "protocolVersion": self.protocolVersion,
            "capabilities": self.capabilities.to_dict() if self.capabilities else {},
            "serverInfo": {
                "name": self.serverInfo.name,
                "version": self.serverInfo.version
            }
        }


@dataclass
class ToolInfo:
    """Tool information"""
    name: str
    description: str
    inputSchema: Dict[str, Any]


@dataclass
class ToolsListRequest(MCPMessage):
    """Tools list request message"""
    pass


@dataclass
class ToolsListResponse(MCPMessage):
    """Tools list response message"""
    tools: List[ToolInfo]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in self.tools
            ]
        }


@dataclass
class ToolsCallRequest(MCPMessage):
    """Tools call request message"""
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolCallResult:
    """Tool call result - follows MCP 2025-06-18 specification"""
    content: List[Dict[str, Any]]
    isError: bool = False
    structuredContent: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "content": self.content,
            "isError": self.isError
        }
        if self.structuredContent is not None:
            result["structuredContent"] = self.structuredContent
        return result


@dataclass
class ToolsCallResponse(MCPMessage):
    """Tools call response message - follows MCP 2025-06-18 specification"""
    content: List[Dict[str, Any]]
    isError: bool = False
    structuredContent: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "content": self.content,
            "isError": self.isError
        }
        if self.structuredContent is not None:
            result["structuredContent"] = self.structuredContent
        return result


# JSON Schema definitions for tool inputs
MEMORY_MESSAGES_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "enum": ["user", "assistant", "system"]
            },
            "content": {
                "type": "string"
            }
        },
        "required": ["role", "content"]
    }
}

IDENTIFIER_SCHEMA = {
    "type": "string",
    "minLength": 1
}

METADATA_SCHEMA = {
    "type": "object",
    "additionalProperties": True
}

# Tool schemas with Context Variables support
ADD_MEMORY_SCHEMA = {
    "type": "object",
    "properties": {
        "messages": MEMORY_MESSAGES_SCHEMA,
        "user_id": IDENTIFIER_SCHEMA,
        "agent_id": IDENTIFIER_SCHEMA, 
        "run_id": IDENTIFIER_SCHEMA,
        "metadata": METADATA_SCHEMA,
        
        # Advanced parameters (all optional for backward compatibility)
        "custom_categories": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": {"type": "string"}
            },
            "description": "Custom categorization rules, format: [{'category': 'description'}]"
        },
        "custom_instructions": {
            "type": "string",
            "description": "Custom memory extraction instructions, overrides default behavior"
        },
        "timestamp": {
            "type": "integer",
            "description": "Unix timestamp (seconds) for memory creation time"
        },
        "version": {
            "type": "string",
            "enum": ["v1", "v2"],
            "description": "API version, v2 enables contextual add"
        },
        "enable_graph": {
            "type": "boolean",
            "description": "Enable graph memory processing for entity extraction"
        },
        "includes": {
            "type": "string",
            "description": "Only include specific types of memories"
        },
        "excludes": {
            "type": "string", 
            "description": "Exclude specific types of memories"
        },
        "output_format": {
            "type": "string",
            "description": "Output format version for response"
        }
    },
    "required": ["messages"],
    "additionalProperties": False
    # Identity parameters are optional when using Context Variables
    # The IdentityManager will resolve from context or arguments
}

SEARCH_MEMORIES_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "minLength": 1
        },
        "user_id": IDENTIFIER_SCHEMA,
        "agent_id": IDENTIFIER_SCHEMA,
        "run_id": IDENTIFIER_SCHEMA,
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100
        },
        "filters": {
            "type": "object",
            "additionalProperties": True
        },
        # Advanced retrieval parameters (supported by core Mem0 service)
        "keyword_search": {
            "type": "boolean",
            "description": "Enable keyword search using BM25 algorithm"
        },
        "rerank": {
            "type": "boolean", 
            "description": "Enable LLM-based reranking of search results"
        },
        "filter_memories": {
            "type": "boolean",
            "description": "Enable intelligent memory filtering"
        },
        "semantic_weight": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Weight for semantic search (0.0-1.0)"
        },
        "keyword_weight": {
            "type": "number", 
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Weight for keyword search (0.0-1.0)"
        },
        "enable_graph": {
            "type": "boolean",
            "description": "Enable graph memory search for entity relationships"
        },
        # Backward compatibility parameters
        "enable_reranking": {
            "type": "boolean",
            "description": "Enable LLM-based reranking (deprecated, use rerank)"
        },
        "enable_filtering": {
            "type": "boolean", 
            "description": "Enable intelligent filtering (deprecated, use filter_memories)"
        },
        "enable_selective_memory": {
            "type": "boolean",
            "description": "Enable selective memory based on importance"
        },
        "output_format": {
            "type": "string",
            "description": "Output format version, use 'v1.1' for graph relations"
        },
        "chart_format": {
            "type": "string",
            "enum": ["mermaid", "cytoscape", "cytoscape.js", "both"],
            "description": "Graph visualization format: mermaid (text-based), cytoscape/cytoscape.js (interactive JSON), both (both formats)"
        }
    },
    "required": ["query"],
    # Identity parameters are optional when using Context Variables
}

GET_MEMORIES_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": IDENTIFIER_SCHEMA,
        "agent_id": IDENTIFIER_SCHEMA,
        "run_id": IDENTIFIER_SCHEMA,
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100
        },
        "list_users": {
            "type": "boolean",
            "description": "Whether to list unique user IDs instead of memories (optional, defaults to false)"
        },
        "filters": {
            "type": "object",
            "description": "Additional filters for memory retrieval (optional)"
        }
    },
    # No required fields - identity resolved from context or arguments
    # Identity parameters are optional when using Context Variables
}

GET_MEMORY_BY_ID_SCHEMA = {
    "type": "object",
    "properties": {
        "memory_id": {
            "type": "string",
            "minLength": 1
        },
        "include_history": {
            "type": "boolean",
            "description": "Whether to include memory history (optional, defaults to false)"
        }
    },
    "required": ["memory_id"]
}

DELETE_MEMORY_SCHEMA = {
    "type": "object",
    "properties": {
        "memory_id": {
            "type": "string",
            "minLength": 1
        }
    },
    "required": ["memory_id"]
}

UPDATE_MEMORY_SCHEMA = {
    "type": "object",
    "properties": {
        "memory_id": {
            "type": "string",
            "minLength": 1
        },
        "data": {
            "type": "string",
            "minLength": 1,
            "description": "New memory content"
        }
    },
    "required": ["memory_id", "data"]
}

BATCH_DELETE_MEMORIES_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": IDENTIFIER_SCHEMA,
        "agent_id": IDENTIFIER_SCHEMA,
        "run_id": IDENTIFIER_SCHEMA,
        "memory_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Array of memory IDs to delete (optional, for specific memory deletion)"
        },
        "reset_all": {
            "type": "boolean",
            "description": "Whether to reset (delete all) memories for the specified user/agent/run (optional, defaults to false)"
        }
    },
    # No required fields - identity resolved from context or arguments  
    # Identity parameters are optional when using Context Variables
}

# Graph Management Schemas have been removed

# Advanced Memory Management Tool Schemas

SELECTIVE_MEMORY_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": IDENTIFIER_SCHEMA,
        "agent_id": IDENTIFIER_SCHEMA,
        "run_id": IDENTIFIER_SCHEMA,
        "operation": {
            "type": "string",
            "enum": ["evaluate", "filter", "selective_add", "analyze"],
            "description": "Operation to perform for selective memory management"
        },
        "content": {
            "type": "string",
            "minLength": 1,
            "description": "Content to evaluate for importance (for evaluate operation)"
        },
        "messages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "enum": ["user", "assistant", "system"]
                    },
                    "content": {
                        "type": "string"
                    }
                },
                "required": ["role", "content"]
            },
            "description": "Messages to add selectively (for selective_add operation)"
        },
        "importance_threshold": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Importance threshold for filtering (0.0 to 1.0)"
        },
        "context": {
            "type": "object",
            "additionalProperties": True,
            "description": "Additional context for importance evaluation"
        },
        "force_add": {
            "type": "boolean",
            "description": "Force add memory even if below threshold (for selective_add)"
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 200,
            "description": "Maximum number of memories to process"
        },
        "metadata": {
            "type": "object",
            "additionalProperties": True,
            "description": "Additional metadata for memory"
        },
        "custom_categories": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": {"type": "string"}
            },
            "description": "Custom categories for memory classification"
        },
        "custom_instructions": {
            "type": "string",
            "description": "Custom instructions for memory processing"
        }
    },
    "required": ["operation"],
    "additionalProperties": False
}

CRITERIA_RETRIEVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "user_id": IDENTIFIER_SCHEMA,
        "agent_id": IDENTIFIER_SCHEMA,
        "run_id": IDENTIFIER_SCHEMA,
        "criteria": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Base search query"
                },
                "time_range": {
                    "type": "object",
                    "properties": {
                        "start": {
                            "type": "string",
                            "description": "Start time (ISO format or relative like '2 days ago')"
                        },
                        "end": {
                            "type": "string", 
                            "description": "End time (ISO format or relative like '1 hour ago')"
                        }
                    },
                    "description": "Time range filter for memories"
                },
                "content_length": {
                    "type": "object",
                    "properties": {
                        "min": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Minimum content length"
                        },
                        "max": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Maximum content length"
                        }
                    },
                    "description": "Content length filter"
                },
                "must_contain": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords that must be present in content"
                },
                "must_not_contain": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords that must not be present in content"
                },
                "relevance_threshold": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Minimum relevance score for results"
                },
                "metadata_filters": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Filters based on memory metadata"
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["relevance", "time", "length", "importance"],
                    "description": "Sort criteria for results"
                },
                "sort_order": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "description": "Sort order (ascending or descending)"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Maximum number of memories to retrieve initially"
                }
            },
            "description": "Complex retrieval criteria"
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "description": "Final limit on number of results to return"
        }
    },
    "required": ["criteria"],
    "additionalProperties": False
}