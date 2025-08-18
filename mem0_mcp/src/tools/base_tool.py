"""
Base tool class for MCP tools
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ..utils.errors import ToolExecutionError
from ..utils.logger import get_logger
from ..identity import IdentityManager, Identity

logger = get_logger(__name__)


@dataclass
class ToolResult:
    """Result of tool execution - follows MCP 2025-06-18 specification"""
    content: List[Dict[str, Any]]
    is_error: bool = False
    structured_content: Optional[Dict[str, Any]] = None  # MCP 2025-06-18 feature
    
    @property
    def success(self) -> bool:
        """Check if the result is successful (not an error)"""
        return not self.is_error
    
    @property 
    def is_success(self) -> bool:
        """Alias for success property for backward compatibility"""
        return not self.is_error
    
    @classmethod
    def success(cls, content: Any, content_type: str = "text", structured_content: Optional[Dict[str, Any]] = None) -> 'ToolResult':
        """Create successful result"""
        if isinstance(content, str):
            content_list = [{"type": content_type, "text": content}]
        elif isinstance(content, list):
            # Assume it's already in the correct format
            content_list = content
        elif isinstance(content, dict):
            # Convert dict to text representation
            import json
            content_list = [{"type": "text", "text": json.dumps(content, indent=2)}]
        else:
            # Convert other types to string
            content_list = [{"type": "text", "text": str(content)}]
        
        return cls(content=content_list, is_error=False, structured_content=structured_content)
    
    @classmethod
    def error(cls, error_message: str) -> 'ToolResult':
        """Create error result"""
        return cls(
            content=[{"type": "text", "text": f"Error: {error_message}"}],
            is_error=True
        )

    @classmethod
    def with_resource_link(cls, uri: str, name: Optional[str] = None,
                          description: Optional[str] = None,
                          mime_type: Optional[str] = None,
                          annotations: Optional[Dict[str, Any]] = None) -> 'ToolResult':
        """
        Create result with resource link (MCP 2025-06-18 feature)

        Args:
            uri: Resource URI
            name: Optional resource name
            description: Optional resource description
            mime_type: Optional MIME type
            annotations: Optional annotations (audience, priority, etc.)
        """
        content_item = {
            "type": "resource_link",
            "uri": uri
        }

        if name:
            content_item["name"] = name
        if description:
            content_item["description"] = description
        if mime_type:
            content_item["mimeType"] = mime_type
        if annotations:
            content_item["annotations"] = annotations

        return cls(content=[content_item], is_error=False)

    @classmethod
    def with_embedded_resource(cls, uri: str, content_data: str,
                              title: Optional[str] = None,
                              mime_type: Optional[str] = None,
                              annotations: Optional[Dict[str, Any]] = None) -> 'ToolResult':
        """
        Create result with embedded resource (MCP 2025-06-18 feature)

        Args:
            uri: Resource URI
            content_data: Resource content
            title: Optional resource title
            mime_type: Optional MIME type
            annotations: Optional annotations
        """
        resource = {
            "uri": uri,
            "text": content_data
        }

        if title:
            resource["title"] = title
        if mime_type:
            resource["mimeType"] = mime_type
        if annotations:
            resource["annotations"] = annotations

        content_item = {
            "type": "resource",
            "resource": resource
        }

        return cls(content=[content_item], is_error=False)

    def to_text(self) -> str:
        """Convert content to text representation"""
        if not self.content:
            return ""
        
        text_parts = []
        for content_item in self.content:
            if isinstance(content_item, dict):
                if content_item.get("type") == "text" and "text" in content_item:
                    text_parts.append(content_item["text"])
                elif content_item.get("type") == "resource_link":
                    text_parts.append(f"Resource: {content_item.get('uri', 'Unknown')}")
                elif content_item.get("type") == "resource":
                    resource = content_item.get("resource", {})
                    text_parts.append(resource.get("text", str(resource)))
                else:
                    # For other content types, convert to string
                    text_parts.append(str(content_item))
            else:
                text_parts.append(str(content_item))
        
        return "\n".join(text_parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "content": self.content,
            "isError": self.is_error
        }
        if self.structured_content is not None:
            result["structuredContent"] = self.structured_content
        return result


class BaseTool(ABC):
    """
    Base class for all MCP tools with Context Variables support
    Supports MCP 2025-06-18 specification features
    """

    def __init__(self, name: str, description: str, title: Optional[str] = None):
        self.name = name
        self.description = description
        self.title = title  # MCP 2025-06-18 feature: optional display name
        self.logger = get_logger(f"{__name__}.{name}")
    
    def get_user_identity(self, arguments: Dict[str, Any] = None) -> Identity:
        """
        Get user identity from context variables or arguments
        
        Args:
            arguments: Optional tool arguments for fallback
            
        Returns:
            Identity object with user information
            
        Raises:
            ToolExecutionError: If no valid identity found
        """
        try:
            # Get effective identity (context takes precedence over arguments)
            identity = IdentityManager.get_effective_identity(arguments)
            
            if not identity.is_valid():
                raise ToolExecutionError(
                    f"No user identity found for {self.name}. "
                    "Please provide user_id, agent_id, or run_id in the tool arguments, "
                    "or use an endpoint with identity in the URL path.",
                    self.name,
                    data={"identity": identity.__dict__}
                )
            
            self.logger.debug(f"Resolved identity for {self.name}: {identity.get_primary_id()}")
            return identity
            
        except Exception as e:
            raise ToolExecutionError(
                f"Error resolving user identity for {self.name}: {str(e)}",
                self.name,
                data={"error": str(e)}
            )
    
    def get_primary_user_id(self, arguments: Dict[str, Any] = None) -> str:
        """
        Get the primary user identifier (user_id, agent_id, or run_id)
        
        Args:
            arguments: Optional tool arguments for fallback
            
        Returns:
            Primary user identifier string
        """
        identity = self.get_user_identity(arguments)
        return identity.get_primary_id()
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given arguments
        
        Args:
            arguments: Tool arguments
            
        Returns:
            ToolResult with execution result
        """
        pass
    
    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for tool input validation

        Returns:
            JSON schema dictionary
        """
        pass

    def get_output_schema(self) -> Optional[Dict[str, Any]]:
        """
        Get JSON schema for tool output validation (MCP 2025-06-18 feature)

        Returns:
            JSON schema dictionary for structured output, or None if not applicable
        """
        return None

    def get_annotations(self) -> Optional[Dict[str, Any]]:
        """
        Get tool annotations (MCP 2025-06-18 feature)

        Returns:
            Annotations dictionary with metadata about tool behavior
        """
        return None

    def get_tool_definition(self, protocol_version: str = "2025-06-18") -> Dict[str, Any]:
        """
        Get complete tool definition for MCP protocol

        Args:
            protocol_version: MCP protocol version to format for

        Returns:
            Tool definition dictionary
        """
        definition = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.get_input_schema()
        }

        # Add MCP 2025-06-18 specific features
        if protocol_version == "2025-06-18":
            if self.title:
                definition["title"] = self.title

            output_schema = self.get_output_schema()
            if output_schema:
                definition["outputSchema"] = output_schema

            annotations = self.get_annotations()
            if annotations:
                definition["annotations"] = annotations

        return definition
    
    async def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        """
        Validate tool arguments against schema
        
        Args:
            arguments: Arguments to validate
            
        Raises:
            ToolExecutionError: If validation fails
        """
        try:
            import jsonschema
            schema = self.get_input_schema()
            jsonschema.validate(arguments, schema)
        except ImportError:
            # If jsonschema is not available, do basic validation
            self.logger.warning("jsonschema not available, doing basic validation")
            await self._basic_validation(arguments)
        except jsonschema.ValidationError as e:
            raise ToolExecutionError(
                f"Invalid arguments for {self.name}: {e.message}",
                self.name,
                data={"validation_error": str(e)}
            )
    
    async def _basic_validation(self, arguments: Dict[str, Any]) -> None:
        """
        Basic argument validation when jsonschema is not available
        
        Args:
            arguments: Arguments to validate
            
        Raises:
            ToolExecutionError: If validation fails
        """
        # Override in subclasses for specific validation
        pass
    
    def __str__(self) -> str:
        return f"Tool({self.name})"
    
    def __repr__(self) -> str:
        return f"Tool(name='{self.name}', description='{self.description}')"