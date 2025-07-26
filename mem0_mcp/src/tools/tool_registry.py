"""
Tool registry for managing MCP tools
"""

from typing import Dict, List, Optional
from .base_tool import BaseTool
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """
    Registry for managing available MCP tools
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        logger.info("Tool registry initialized")
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        Register a tool
        
        Args:
            tool: Tool to register
        """
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool
        
        Args:
            tool_name: Name of tool to unregister
            
        Returns:
            True if tool was unregistered, False if not found
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        
        logger.warning(f"Tool '{tool_name}' not found for unregistration")
        return False
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a registered tool
        
        Args:
            tool_name: Name of tool to get
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[BaseTool]:
        """
        Get list of all registered tools
        
        Returns:
            List of registered tools
        """
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """
        Get list of all registered tool names
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def has_tool(self, tool_name: str) -> bool:
        """
        Check if tool is registered
        
        Args:
            tool_name: Name of tool to check
            
        Returns:
            True if tool is registered, False otherwise
        """
        return tool_name in self._tools
    
    def clear(self) -> None:
        """Clear all registered tools"""
        count = len(self._tools)
        self._tools.clear()
        logger.info(f"Cleared {count} tools from registry")
    
    def __len__(self) -> int:
        """Get number of registered tools"""
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        """Check if tool is registered using 'in' operator"""
        return self.has_tool(tool_name)
    
    def __iter__(self):
        """Iterate over tool names"""
        return iter(self._tools.keys())
    
    def __repr__(self) -> str:
        return f"ToolRegistry({len(self._tools)} tools: {list(self._tools.keys())})"