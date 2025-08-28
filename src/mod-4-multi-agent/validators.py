"""
Input validators for the Abandoned Order Detection System.
Ensures all inputs are safe and within expected ranges.
"""

from typing import Optional


def validate_order_id(order_id: int) -> int:
    """
    Validate order ID is within safe range.
    
    Args:
        order_id: The order ID to validate
        
    Returns:
        Validated order ID
        
    Raises:
        ValueError: If order ID is invalid
    """
    if not isinstance(order_id, int):
        raise ValueError(f"Order ID must be an integer, got {type(order_id)}")
    
    if order_id <= 0:
        raise ValueError(f"Order ID must be positive, got {order_id}")
    
    if order_id > 1_000_000:
        raise ValueError(f"Order ID out of range: {order_id}")
    
    return order_id


def validate_driver_id(driver_id: int) -> int:
    """
    Validate driver ID is within safe range.
    
    Args:
        driver_id: The driver ID to validate
        
    Returns:
        Validated driver ID
        
    Raises:
        ValueError: If driver ID is invalid
    """
    if not isinstance(driver_id, int):
        raise ValueError(f"Driver ID must be an integer, got {type(driver_id)}")
    
    if driver_id <= 0:
        raise ValueError(f"Driver ID must be positive, got {driver_id}")
    
    if driver_id > 100_000:
        raise ValueError(f"Driver ID out of range: {driver_id}")
    
    return driver_id


def validate_threshold_minutes(minutes: int) -> int:
    """
    Validate threshold minutes is within reasonable range.
    
    Args:
        minutes: The threshold in minutes
        
    Returns:
        Validated minutes
        
    Raises:
        ValueError: If minutes is invalid
    """
    if not isinstance(minutes, int):
        raise ValueError(f"Minutes must be an integer, got {type(minutes)}")
    
    if minutes < 0:
        raise ValueError(f"Minutes cannot be negative, got {minutes}")
    
    if minutes > 1440:  # 24 hours
        raise ValueError(f"Threshold too high (>24 hours): {minutes}")
    
    return minutes


def mask_sensitive_string(value: str, show_chars: int = 4) -> str:
    """
    Mask sensitive string values for logging.
    
    Args:
        value: The string to mask
        show_chars: Number of characters to show at the end
        
    Returns:
        Masked string
    """
    if not value or len(value) <= show_chars:
        return "***"
    
    return f"***{value[-show_chars:]}"