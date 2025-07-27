"""
Timestamp validation and conversion utilities for Mem0.

This module provides functions for validating and converting Unix timestamps,
based on the existing TypeScript validation logic from Redis vector store.
"""

import datetime
import logging
from typing import Union

logger = logging.getLogger(__name__)

# Unix epoch start time (January 1, 1970 00:00:00 UTC)
UNIX_EPOCH_START = 0

# Maximum reasonable timestamp (year 2100)
MAX_REASONABLE_TIMESTAMP = 4102444800  # 2100-01-01 00:00:00 UTC


def validate_unix_timestamp(timestamp: Union[int, float, str]) -> datetime.datetime:
    """
    Validate and convert Unix timestamp to UTC datetime object.
    
    Based on the TypeScript validation logic from mem0-ts/src/oss/src/vector_stores/redis.ts.
    Supports both seconds (10 digits) and milliseconds (13 digits) formats.
    
    Args:
        timestamp: Unix timestamp as int, float, or string
        
    Returns:
        datetime.datetime: UTC datetime object
        
    Raises:
        ValueError: If timestamp is invalid or out of range
        TypeError: If timestamp type is not supported
    """
    try:
        # Convert to number
        if isinstance(timestamp, str):
            timestamp_num = float(timestamp)
        elif isinstance(timestamp, (int, float)):
            timestamp_num = float(timestamp)
        else:
            raise TypeError(f"Timestamp must be int, float, or string, got {type(timestamp)}")
        
        # Check if timestamp is in milliseconds (13 digits) or seconds (10 digits)
        timestamp_str = str(int(timestamp_num))
        if len(timestamp_str) == 13:
            # Milliseconds - convert to seconds
            timestamp_seconds = timestamp_num / 1000
        elif len(timestamp_str) == 10:
            # Seconds
            timestamp_seconds = timestamp_num
        else:
            raise ValueError(f"Invalid timestamp format: {timestamp}. Expected 10 digits (seconds) or 13 digits (milliseconds)")
        
        # Validate timestamp range
        if not is_valid_timestamp_range(timestamp_seconds):
            raise ValueError(f"Timestamp {timestamp_seconds} is out of valid range")
        
        # Convert to UTC datetime
        return convert_timestamp_to_utc_datetime(timestamp_seconds)
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Error validating timestamp {timestamp}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error validating timestamp {timestamp}: {e}")
        raise ValueError(f"Failed to validate timestamp: {e}")


def is_valid_timestamp_range(timestamp: float) -> bool:
    """
    Check if timestamp is within valid range.
    
    Args:
        timestamp: Unix timestamp in seconds
        
    Returns:
        bool: True if timestamp is valid, False otherwise
    """
    try:
        # Check minimum bound (Unix epoch start)
        if timestamp < UNIX_EPOCH_START:
            logger.warning(f"Timestamp {timestamp} is before Unix epoch (1970-01-01)")
            return False
        
        # Check maximum bound (not in the future + reasonable upper limit)
        current_time = datetime.datetime.now(datetime.timezone.utc).timestamp()
        if timestamp > current_time:
            logger.warning(f"Timestamp {timestamp} is in the future (current: {current_time})")
            return False
        
        if timestamp > MAX_REASONABLE_TIMESTAMP:
            logger.warning(f"Timestamp {timestamp} is beyond reasonable limit (year 2100)")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking timestamp range for {timestamp}: {e}")
        return False


def convert_timestamp_to_utc_datetime(timestamp: float) -> datetime.datetime:
    """
    Convert Unix timestamp to UTC datetime object.
    
    Args:
        timestamp: Unix timestamp in seconds
        
    Returns:
        datetime.datetime: UTC datetime object
        
    Raises:
        ValueError: If timestamp cannot be converted to valid datetime
    """
    try:
        # Create datetime from timestamp
        dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
        
        # Validate the datetime is valid (not NaN equivalent)
        if dt.year < 1970 or dt.year > 2100:
            raise ValueError(f"Converted datetime {dt} is out of reasonable range")
        
        return dt
        
    except (ValueError, OSError) as e:
        logger.error(f"Error converting timestamp {timestamp} to datetime: {e}")
        raise ValueError(f"Invalid timestamp {timestamp}: {e}")


def get_current_utc_time() -> datetime.datetime:
    """
    Get current UTC time.
    
    Returns:
        datetime.datetime: Current UTC datetime
    """
    return datetime.datetime.now(datetime.timezone.utc)


def format_timestamp_for_storage(dt: datetime.datetime) -> str:
    """
    Format datetime object for storage in metadata.
    
    Args:
        dt: datetime object (should be UTC)
        
    Returns:
        str: ISO format string
    """
    # Ensure timezone is UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    elif dt.tzinfo != datetime.timezone.utc:
        dt = dt.astimezone(datetime.timezone.utc)
    
    return dt.isoformat()
