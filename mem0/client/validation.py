"""
Validation utilities for mem0 client parameters.

This module provides validation functions for client parameters to ensure
data integrity and provide clear error messages for invalid inputs.
"""

from typing import Dict, List, Optional


def validate_custom_categories(custom_categories: List[Dict[str, str]]) -> None:
    """Validate custom_categories parameter format.

    Validates that custom_categories follows the required format:
    [{"category_name": "description"}, ...]

    Args:
        custom_categories: List of category dictionaries to validate.
                          Each dictionary should have string keys and string values.
                          Keys cannot be empty or whitespace-only.

    Raises:
        ValueError: If the format is invalid. Error messages include:
                   - "custom_categories must be a list"
                   - "Category at index {i} must be a dictionary"
                   - "Category at index {i} cannot be empty"
                   - "Category at index {i}: both key and value must be strings"
                   - "Category at index {i}: key cannot be empty or whitespace-only"

    Examples:
        >>> validate_custom_categories([{"work": "Work related memories"}])
        # No exception raised

        >>> validate_custom_categories([{"": "Empty key"}])
        ValueError: Category at index 0: key cannot be empty or whitespace-only
    """
    if not isinstance(custom_categories, list):
        raise ValueError("custom_categories must be a list")
    
    for i, category in enumerate(custom_categories):
        if not isinstance(category, dict):
            raise ValueError(f"Category at index {i} must be a dictionary")
        
        if not category:
            raise ValueError(f"Category at index {i} cannot be empty")
        
        for key, value in category.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError(f"Category at index {i}: both key and value must be strings")
            if not key.strip():
                raise ValueError(f"Category at index {i}: key cannot be empty or whitespace-only")


def validate_custom_instructions(custom_instructions: Optional[str]) -> None:
    """Validate custom_instructions parameter format.

    Validates that custom_instructions is a non-empty string within length limits.

    Args:
        custom_instructions: Custom instructions string to validate.
                           Must be a string if provided, cannot be empty or whitespace-only.
                           Maximum length is 10000 characters.

    Raises:
        ValueError: If the format is invalid. Error messages include:
                   - "custom_instructions must be a string"
                   - "custom_instructions cannot be empty or whitespace-only"
                   - "custom_instructions too long (max 10000 characters)"

    Examples:
        >>> validate_custom_instructions("Extract key facts from conversations")
        # No exception raised

        >>> validate_custom_instructions("")
        ValueError: custom_instructions cannot be empty or whitespace-only

        >>> validate_custom_instructions(123)
        ValueError: custom_instructions must be a string
    """
    if custom_instructions is not None:
        if not isinstance(custom_instructions, str):
            raise ValueError("custom_instructions must be a string")

        if not custom_instructions.strip():
            raise ValueError("custom_instructions cannot be empty or whitespace-only")

        if len(custom_instructions) > 10000:
            raise ValueError("custom_instructions too long (max 10000 characters)")
