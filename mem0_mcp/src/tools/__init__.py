"""
MCP Tools package implementing hybrid architecture design
"""

from .memory_tools import (
    AddMemoryTool,
    SearchMemoriesTool,
    GetMemoriesTool,
    GetMemoryByIdTool,
    DeleteMemoryTool,
    UpdateMemoryTool,

    MemoryToolsExecutor
)

from .advanced_tools import (
    SelectiveMemoryTool,
    CriteriaRetrievalTool,
    ManageGraphEntitiesTool,
    BatchOperationsTool
)

from .tool_manager import ToolManager, create_tool_manager
from .tool_registry import ToolRegistry
from .base_tool import BaseTool, ToolResult

__all__ = [
    # Core memory tools (Tier 1)
    "AddMemoryTool",
    "SearchMemoriesTool",
    "GetMemoriesTool",
    "GetMemoryByIdTool",
    "DeleteMemoryTool",
    "UpdateMemoryTool",

    "MemoryToolsExecutor",

    # Advanced tools (Tier 2)
    "SelectiveMemoryTool",
    "CriteriaRetrievalTool",
    "ManageGraphEntitiesTool",
    "BatchOperationsTool",

    # Management components
    "ToolManager",
    "create_tool_manager",
    "ToolRegistry",

    # Base classes
    "BaseTool",
    "ToolResult"
]