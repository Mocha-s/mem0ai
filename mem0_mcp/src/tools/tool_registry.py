"""
Tool registry for managing tool definitions and metadata
"""

import json
import os
from typing import Dict, List, Any, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """
    Registry for managing tool definitions and metadata.
    Loads tool definitions from tools.json and provides access to tool information.
    """
    
    def __init__(self, registry_file: str = "tools.json"):
        self.registry_file = registry_file
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._load_tools()
    
    def _load_tools(self):
        """Load tools from the registry file"""
        try:
            # Try to find tools.json in the project root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, "..", "..")
            registry_path = os.path.join(project_root, self.registry_file)
            
            if not os.path.exists(registry_path):
                # Try current directory
                registry_path = self.registry_file
            
            if os.path.exists(registry_path):
                with open(registry_path, 'r', encoding='utf-8') as f:
                    tools_list = json.load(f)
                
                # Convert list to dict for easier access
                for tool in tools_list:
                    self.tools[tool['name']] = tool
                
                logger.info(f"Loaded {len(self.tools)} tools from {registry_path}")
            else:
                logger.warning(f"Tool registry file not found: {registry_path}")
                self._create_default_registry()
                
        except Exception as e:
            logger.error(f"Error loading tool registry: {e}")
            self._create_default_registry()
    
    def _create_default_registry(self):
        """Create a default tool registry with basic tools"""
        self.tools = {
            "add_memory": {
                "name": "add_memory",
                "description": "Enhanced tool for adding memories with contextual processing",
                "version": "2.0.0",
                "endpoint": "/add_memory",
                "module": "mem0_mcp.src.tools.services.add_memory_service.router",
                "dependencies": []
            },
            "search_memories": {
                "name": "search_memories", 
                "description": "Enhanced tool for searching memories with advanced retrieval",
                "version": "2.0.0",
                "endpoint": "/search_memories",
                "module": "mem0_mcp.src.tools.services.search_memories_service.router",
                "dependencies": []
            },
            "get_memories": {
                "name": "get_memories",
                "description": "Get memories for a user",
                "version": "2.0.0", 
                "endpoint": "/get_memories",
                "module": "mem0_mcp.src.tools.services.get_memories_service.router",
                "dependencies": []
            },
            "update_memory": {
                "name": "update_memory",
                "description": "Update an existing memory",
                "version": "2.0.0",
                "endpoint": "/update_memory", 
                "module": "mem0_mcp.src.tools.services.update_memory_service.router",
                "dependencies": []
            },
            "delete_memory": {
                "name": "delete_memory",
                "description": "Delete a specific memory",
                "version": "2.0.0",
                "endpoint": "/delete_memory",
                "module": "mem0_mcp.src.tools.services.delete_memory_service.router", 
                "dependencies": []
            },
            "get_memory_by_id": {
                "name": "get_memory_by_id",
                "description": "Get a specific memory by its ID",
                "version": "2.0.0",
                "endpoint": "/get_memory_by_id",
                "module": "mem0_mcp.src.tools.services.get_memory_by_id_service.router",
                "dependencies": []
            },
            "batch_delete_memories": {
                "name": "batch_delete_memories",
                "description": "Delete multiple memories in a batch operation",
                "version": "2.0.0",
                "endpoint": "/batch_delete_memories",
                "module": "mem0_mcp.src.tools.services.batch_delete_memories_service.router",
                "dependencies": []
            },
            "selective_memory": {
                "name": "selective_memory",
                "description": "Evaluate and selectively manage memories based on importance",
                "version": "2.0.0",
                "endpoint": "/selective_memory",
                "module": "mem0_mcp.src.tools.services.selective_memory_service.router",
                "dependencies": []
            },
            "criteria_retrieval": {
                "name": "criteria_retrieval",
                "description": "Retrieve memories using complex criteria and multi-dimensional filtering",
                "version": "2.0.0",
                "endpoint": "/criteria_retrieval",
                "module": "mem0_mcp.src.tools.services.criteria_retrieval_service.router",
                "dependencies": []
            }
        }
        logger.info(f"Created default tool registry with {len(self.tools)} tools")
    
    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool definition by name"""
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all tool definitions"""
        return self.tools.copy()
    
    def get_tool_names(self) -> List[str]:
        """Get list of all tool names"""
        return list(self.tools.keys())
    
    def register_tool(self, tool_definition: Dict[str, Any]):
        """Register a new tool"""
        tool_name = tool_definition.get('name')
        if not tool_name:
            raise ValueError("Tool definition must include 'name' field")
        
        self.tools[tool_name] = tool_definition
        logger.info(f"Registered tool: {tool_name}")
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        return False
    
    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get tools by category"""
        return [tool for tool in self.tools.values() if tool.get('category') == category]
    
    def get_tool_dependencies(self, tool_name: str) -> List[str]:
        """Get dependencies for a tool"""
        tool = self.get_tool(tool_name)
        if tool:
            return tool.get('dependencies', [])
        return []
    
    def validate_tool_definition(self, tool_definition: Dict[str, Any]) -> bool:
        """Validate a tool definition"""
        required_fields = ['name', 'description', 'endpoint']
        
        for field in required_fields:
            if field not in tool_definition:
                logger.error(f"Tool definition missing required field: {field}")
                return False
        
        return True
    
    def reload_registry(self):
        """Reload the tool registry from file"""
        self.tools.clear()
        self._load_tools()
    
    def save_registry(self, output_file: Optional[str] = None):
        """Save the current registry to file"""
        output_file = output_file or self.registry_file
        
        try:
            # Convert dict back to list format
            tools_list = list(self.tools.values())
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tools_list, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved tool registry to {output_file}")
            
        except Exception as e:
            logger.error(f"Error saving tool registry: {e}")
            raise
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the tool registry"""
        stats = {
            "total_tools": len(self.tools),
            "tools_by_version": {},
            "tools_with_dependencies": 0,
            "average_dependencies": 0
        }
        
        total_deps = 0
        for tool in self.tools.values():
            version = tool.get('version', 'unknown')
            stats["tools_by_version"][version] = stats["tools_by_version"].get(version, 0) + 1
            
            deps = tool.get('dependencies', [])
            if deps:
                stats["tools_with_dependencies"] += 1
                total_deps += len(deps)
        
        if stats["tools_with_dependencies"] > 0:
            stats["average_dependencies"] = total_deps / stats["tools_with_dependencies"]
        
        return stats


# Global registry instance
_registry_instance = None

def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance
