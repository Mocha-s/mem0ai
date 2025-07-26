"""
Environment variable parsing utilities for Mem0 configuration system.

This module provides utilities to parse environment variables in configuration
dictionaries, supporting the 'env:VARIABLE_NAME' format for dynamic configuration.
"""

import os
import logging
from typing import Any, Dict, Union

logger = logging.getLogger(__name__)


def parse_environment_variables(config_dict: Union[Dict[str, Any], Any]) -> Union[Dict[str, Any], Any]:
    """
    Parse environment variables in config values recursively.
    
    Converts 'env:VARIABLE_NAME' strings to actual environment variable values.
    Supports nested dictionaries and provides comprehensive error handling.
    
    Args:
        config_dict: Configuration dictionary or any value to parse
        
    Returns:
        Parsed configuration with environment variables resolved
        
    Examples:
        >>> config = {"api_key": "env:OPENAI_API_KEY", "model": "gpt-4o-mini"}
        >>> parse_environment_variables(config)
        {"api_key": "sk-...", "model": "gpt-4o-mini"}
    """
    if isinstance(config_dict, dict):
        parsed_config = {}
        for key, value in config_dict.items():
            parsed_config[key] = _parse_value(value, key)
        return parsed_config
    else:
        return _parse_value(config_dict)


def _parse_value(value: Any, key: str = None) -> Any:
    """
    Parse a single configuration value for environment variables.
    
    Args:
        value: The value to parse
        key: Optional key name for logging context
        
    Returns:
        Parsed value with environment variables resolved
    """
    if isinstance(value, str) and value.startswith("env:"):
        return _resolve_environment_variable(value, key)
    elif isinstance(value, dict):
        return parse_environment_variables(value)
    elif isinstance(value, list):
        return [_parse_value(item) for item in value]
    else:
        return value


def _resolve_environment_variable(env_string: str, key: str = None) -> str:
    """
    Resolve a single environment variable string.
    
    Args:
        env_string: String in format 'env:VARIABLE_NAME'
        key: Optional key name for logging context
        
    Returns:
        Environment variable value or original string if not found
    """
    try:
        env_var = env_string.split(":", 1)[1]
        env_value = os.environ.get(env_var)
        
        if env_value is not None:
            context = f" for {key}" if key else ""
            logger.info(f"Loaded environment variable {env_var}{context}")
            return env_value
        else:
            context = f" for {key}" if key else ""
            logger.warning(f"Environment variable {env_var} not found{context}, keeping original value")
            return env_string
            
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid environment variable format: {env_string}. Error: {e}")
        return env_string


def get_env_with_default(env_var: str, default: Any = None) -> Any:
    """
    Get environment variable with default value.
    
    Args:
        env_var: Environment variable name
        default: Default value if environment variable is not set
        
    Returns:
        Environment variable value or default
    """
    value = os.environ.get(env_var)
    if value is not None:
        logger.info(f"Using environment variable {env_var}")
        return value
    else:
        logger.debug(f"Environment variable {env_var} not set, using default: {default}")
        return default


def validate_required_env_vars(required_vars: list) -> Dict[str, str]:
    """
    Validate that required environment variables are set.
    
    Args:
        required_vars: List of required environment variable names
        
    Returns:
        Dictionary of environment variable names and values
        
    Raises:
        ValueError: If any required environment variable is missing
    """
    missing_vars = []
    env_values = {}
    
    for var in required_vars:
        value = os.environ.get(var)
        if value is None:
            missing_vars.append(var)
        else:
            env_values[var] = value
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return env_values


def parse_bool_env(env_var: str, default: bool = False) -> bool:
    """
    Parse boolean environment variable.
    
    Args:
        env_var: Environment variable name
        default: Default boolean value
        
    Returns:
        Boolean value parsed from environment variable
    """
    value = os.environ.get(env_var, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    else:
        return default


def parse_int_env(env_var: str, default: int = 0) -> int:
    """
    Parse integer environment variable.
    
    Args:
        env_var: Environment variable name
        default: Default integer value
        
    Returns:
        Integer value parsed from environment variable
    """
    try:
        value = os.environ.get(env_var)
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        logger.warning(f"Invalid integer value for {env_var}, using default: {default}")
        return default


def parse_float_env(env_var: str, default: float = 0.0) -> float:
    """
    Parse float environment variable.
    
    Args:
        env_var: Environment variable name
        default: Default float value
        
    Returns:
        Float value parsed from environment variable
    """
    try:
        value = os.environ.get(env_var)
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        logger.warning(f"Invalid float value for {env_var}, using default: {default}")
        return default
