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
            "capabilities": {
                "tools": self.capabilities.tools or {},
                "resources": self.capabilities.resources or {},
                "prompts": self.capabilities.prompts or {},
                "logging": self.capabilities.logging or {}
            },
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
    """Tool call result"""
    content: List[Dict[str, Any]]
    isError: bool = False


@dataclass
class ToolsCallResponse(MCPMessage):
    """Tools call response message"""
    content: List[Dict[str, Any]]
    isError: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "content": self.content,
            "isError": self.isError
        }


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
        "metadata": METADATA_SCHEMA
    },
    "required": ["messages"],
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
        "run_id": IDENTIFIER_SCHEMA
    },
    # No required fields - identity resolved from context or arguments  
    # Identity parameters are optional when using Context Variables
}