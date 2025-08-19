"""
Mem0 MCP Server Package

A Model Context Protocol server providing intelligent memory capabilities.
"""

__version__ = "0.1.0"
__author__ = "Mem0 Team"
__description__ = "MCP server for Mem0 intelligent memory operations"

from .server import MCPServer

__all__ = ["MCPServer"]