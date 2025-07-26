"""
Logging utilities for Mem0 MCP Server
"""

import logging
import sys
from typing import Optional
from ..config.constants import LOG_FORMAT, LOG_LEVEL


def setup_logging(
    level: str = LOG_LEVEL,
    log_to_file: bool = False,
    log_file_path: Optional[str] = None,
    format_string: str = LOG_FORMAT
) -> None:
    """
    Setup logging configuration for MCP server
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_file_path: Path to log file (if log_to_file is True)
        format_string: Log message format
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Setup handlers
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_to_file and log_file_path:
        handlers.append(logging.FileHandler(log_file_path))
    
    # Configure logging
    logging.basicConfig(
        level=numeric_level,
        format=format_string,
        handlers=handlers,
        force=True  # Override existing configuration
    )
    
    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)