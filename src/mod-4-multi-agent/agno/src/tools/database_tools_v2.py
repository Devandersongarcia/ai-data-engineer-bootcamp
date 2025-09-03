# src/tools/database_tools_v2.py - Database Tools for UberEats Agents (Agno Compatible)
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union
import psycopg2
import redis
from agno.tools import function
from pydantic import BaseModel, Field

from ..config.settings import settings

logger = logging.getLogger(__name__)


@function
def postgres_query(
    query: str = Field(..., description="SQL query to execute"),
    params: Optional[List[Any]] = Field(default=None, description="Query parameters"),
    fetch_all: bool = Field(default=True, description="Whether to fetch all results or just one")
) -> Dict[str, Any]:
    """
    Execute PostgreSQL queries to access UberEats database
    
    Enables agents to:
    - Query order data in real-time
    - Access restaurant information
    - Retrieve driver details
    - Perform business analytics queries
    """
    try:
        # Safety check for dangerous operations
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'UPDATE']
        if any(keyword in query.upper() for keyword in dangerous_keywords):
            if 'UPDATE' not in query.upper():  # Allow SELECT...UPDATE patterns
                return {
                    "success": False,
                    "error": "Dangerous query operations not allowed",
                    "allowed_operations": ["SELECT", "WITH (for SELECT)"]
                }
        
        # For demo purposes, return sample data instead of actual DB query
        sample_data = _get_sample_database_data(query)
        
        return {
            "success": True,
            "data": sample_data,
            "row_count": len(sample_data) if isinstance(sample_data, list) else 1,
            "query": query
        }
        
    except Exception as e:
        logger.error(f"PostgreSQL query error: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query
        }


@function
def redis_operation(
    operation: str = Field(..., description="Operation: get, set, delete, exists, keys, ttl"),
    key: str = Field(..., description="Redis key"),
    value: Optional[Any] = Field(default=None, description="Value for set operations"),
    ttl: Optional[int] = Field(default=None, description="Time to live in seconds")
) -> Dict[str, Any]:
    """
    Perform Redis operations for caching and real-time data
    
    Enables agents to:
    - Cache expensive calculations
    - Store temporary session data
    - Manage real-time counters
    - Implement pub/sub messaging
    """
    try:
        # Simulate Redis operations for demo
        operation = operation.lower()
        
        if operation == "get":
            # Simulate getting cached data
            sample_value = _get_sample_redis_data(key)
            return {
                "success": True,
                "operation": "get",
                "key": key,
                "value": sample_value,
                "found": sample_value is not None
            }
        
        elif operation == "set":
            if value is None:
                return {
                    "success": False,
                    "error": "Value is required for set operation"
                }
            
            # Simulate storing data
            logger.info(f"Redis SET: {key} = {value} (TTL: {ttl})")
            
            return {
                "success": True,
                "operation": "set",
                "key": key,
                "ttl": ttl
            }
        
        elif operation == "delete":
            logger.info(f"Redis DELETE: {key}")
            return {
                "success": True,
                "operation": "delete",
                "key": key,
                "deleted": True
            }
        
        elif operation == "exists":
            # Simulate key existence check
            exists = key.startswith(("eta_", "order_", "driver_"))
            return {
                "success": True,
                "operation": "exists",
                "key": key,
                "exists": exists
            }
        
        elif operation == "keys":
            # Simulate key pattern search
            pattern = key if key else "*"
            sample_keys = [
                "eta_prediction:ORD2024001",
                "driver_location:D001",
                "order_status:ORD2024002"
            ]
            matching_keys = [k for k in sample_keys if pattern == "*" or pattern in k]
            
            return {
                "success": True,
                "operation": "keys",
                "pattern": pattern,
                "keys": matching_keys,
                "count": len(matching_keys)
            }
        
        else:
            return {
                "success": False,
                "error": f"Unsupported operation: {operation}",
                "supported_operations": ["get", "set", "delete", "exists", "keys", "ttl"]
            }
            
    except Exception as e:
        logger.error(f"Redis operation error: {e}")
        return {
            "success": False,
            "error": str(e),
            "operation": operation
        }


def _get_sample_database_data(query: str) -> List[Dict[str, Any]]:
    """Generate sample database data based on query"""
    query_lower = query.lower()
    
    if "orders" in query_lower:
        return [
            {
                "order_id": "ORD2024001",
                "customer_id": "CUST001",
                "restaurant_id": "REST001",
                "status": "preparing",
                "order_time": "2024-01-15 18:30:00",
                "total_amount": 45.50
            },
            {
                "order_id": "ORD2024002",
                "customer_id": "CUST002", 
                "restaurant_id": "REST002",
                "status": "ready",
                "order_time": "2024-01-15 18:45:00",
                "total_amount": 32.75
            }
        ]
    
    elif "drivers" in query_lower:
        return [
            {
                "driver_id": "D001",
                "current_location": "37.7749,-122.4194",
                "status": "available",
                "rating": 4.8,
                "vehicle_type": "car"
            },
            {
                "driver_id": "D002",
                "current_location": "37.7849,-122.4094",
                "status": "available", 
                "rating": 4.6,
                "vehicle_type": "scooter"
            }
        ]
    
    elif "restaurants" in query_lower:
        return [
            {
                "restaurant_id": "REST001",
                "name": "Downtown Bistro",
                "current_capacity": 0.7,
                "average_prep_time": 15,
                "is_open": True
            },
            {
                "restaurant_id": "REST002",
                "name": "Pizza Palace",
                "current_capacity": 0.8,
                "average_prep_time": 20,
                "is_open": True
            }
        ]
    
    else:
        return [{"message": "Sample query result", "query": query}]


def _get_sample_redis_data(key: str) -> Any:
    """Generate sample Redis data based on key"""
    if key.startswith("eta_prediction"):
        return {
            "order_id": "ORD2024001",
            "eta_minutes": 28.5,
            "factors": {
                "distance_km": 3.2,
                "weather_condition": "clear",
                "traffic": "moderate"
            }
        }
    
    elif key.startswith("driver_location"):
        return "37.7749,-122.4194"
    
    elif key.startswith("order_status"):
        return "preparing"
    
    return None


# Example queries for UberEats use cases
UBEREATS_QUERIES = {
    "active_orders": """
        SELECT order_id, customer_id, restaurant_id, status, order_time, total_amount 
        FROM orders 
        WHERE status IN ('placed', 'confirmed', 'preparing', 'ready') 
        ORDER BY order_time DESC 
        LIMIT 50
    """,
    
    "available_drivers": """
        SELECT driver_id, current_location, status, rating, vehicle_type 
        FROM drivers 
        WHERE status = 'available' 
        AND rating >= 4.0
        ORDER BY rating DESC
    """,
    
    "restaurant_capacity": """
        SELECT restaurant_id, name, current_capacity, average_prep_time, is_open
        FROM restaurants 
        WHERE is_open = true 
        AND current_capacity < 0.9
        ORDER BY current_capacity ASC
    """
}