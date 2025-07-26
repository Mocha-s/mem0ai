"""
Parameter validation utilities
"""

from typing import Any, Dict, List, Optional, Union
from .errors import ValidationError


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """
    Validate that all required fields are present in data
    
    Args:
        data: Data dictionary to validate
        required_fields: List of required field names
        
    Raises:
        ValidationError: If any required field is missing
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    
    if missing_fields:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing_fields)}",
            data={"missing_fields": missing_fields}
        )


def validate_memory_params(params: Dict[str, Any]) -> None:
    """
    Validate parameters for memory operations
    
    Args:
        params: Parameters to validate
        
    Raises:
        ValidationError: If validation fails
    """
    # For add_memory operations
    if "messages" in params:
        if not isinstance(params["messages"], list):
            raise ValidationError("Messages must be a list")
        
        if not params["messages"]:
            raise ValidationError("Messages list cannot be empty")
        
        for i, message in enumerate(params["messages"]):
            if not isinstance(message, dict):
                raise ValidationError(f"Message at index {i} must be a dictionary")
            
            if "content" not in message:
                raise ValidationError(f"Message at index {i} must have 'content' field")
    
    # Validate identifiers (at least one should be present)
    identifiers = ["user_id", "agent_id", "run_id"]
    if not any(params.get(field) for field in identifiers):
        raise ValidationError("At least one identifier (user_id, agent_id, or run_id) is required")
    
    # Validate metadata if present
    if "metadata" in params and params["metadata"] is not None:
        if not isinstance(params["metadata"], dict):
            raise ValidationError("Metadata must be a dictionary")


def validate_search_params(params: Dict[str, Any]) -> None:
    """
    Validate parameters for search operations
    
    Args:
        params: Parameters to validate
        
    Raises:
        ValidationError: If validation fails
    """
    # Query is required for search
    if "query" not in params or not params["query"]:
        raise ValidationError("Query parameter is required for search operations")
    
    if not isinstance(params["query"], str):
        raise ValidationError("Query must be a string")
    
    # Validate identifiers (at least one should be present)
    identifiers = ["user_id", "agent_id", "run_id"]
    if not any(params.get(field) for field in identifiers):
        raise ValidationError("At least one identifier (user_id, agent_id, or run_id) is required")
    
    # Validate limit if present
    if "limit" in params:
        try:
            limit = int(params["limit"])
            if limit <= 0 or limit > 100:
                raise ValidationError("Limit must be between 1 and 100")
        except (ValueError, TypeError):
            raise ValidationError("Limit must be a valid integer")


def validate_memory_id(memory_id: Union[str, int]) -> str:
    """
    Validate and normalize memory ID
    
    Args:
        memory_id: Memory ID to validate
        
    Returns:
        Normalized memory ID as string
        
    Raises:
        ValidationError: If memory ID is invalid
    """
    if not memory_id:
        raise ValidationError("Memory ID is required")
    
    # Convert to string and validate format
    memory_id_str = str(memory_id).strip()
    
    if not memory_id_str:
        raise ValidationError("Memory ID cannot be empty")
    
    return memory_id_str


def validate_batch_delete_params(params: Dict[str, Any]) -> None:
    """
    Validate parameters for batch delete operations
    
    Args:
        params: Parameters to validate
        
    Raises:
        ValidationError: If validation fails
    """
    # At least one identifier is required
    identifiers = ["user_id", "agent_id", "run_id"]
    if not any(params.get(field) for field in identifiers):
        raise ValidationError("At least one identifier (user_id, agent_id, or run_id) is required")