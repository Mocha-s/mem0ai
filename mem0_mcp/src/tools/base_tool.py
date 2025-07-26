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
    """Result of tool execution"""
    content: List[Dict[str, Any]]
    is_error: bool = False
    
    @classmethod
    def success(cls, content: Any, content_type: str = "text") -> 'ToolResult':
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
        
        return cls(content=content_list, is_error=False)
    
    @classmethod
    def error(cls, error_message: str) -> 'ToolResult':
        """Create error result"""
        return cls(
            content=[{"type": "text", "text": f"Error: {error_message}"}],
            is_error=True
        )


class BaseTool(ABC):
    """
    Base class for all MCP tools with Context Variables support
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
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