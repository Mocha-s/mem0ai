#!/usr/bin/env python3
"""
Startup script for Mem0 MCP Server
"""

import os
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.server import main

if __name__ == "__main__":
    main()