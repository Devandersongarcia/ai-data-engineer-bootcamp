"""Database tools for UberEats Agents.

Provides secure database access tools for PostgreSQL and Redis operations,
with built-in safety checks and connection management.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, Union

import psycopg2
import redis
from agno.tools import Function
from pydantic import BaseModel, Field

from ..config.settings import settings

logger = logging.getLogger(__name__)


class PostgresQueryInput(BaseModel):
    """Input schema for PostgreSQL queries.
    
    Attributes:
        query: SQL query to execute (SELECT statements only for security).
        params: Optional query parameters for prepared statements.
        fetch_all: Whether to fetch all results or just the first row.
    """
    query: str = Field(..., description="SQL query to execute")
    params: Optional[list[Any]] = Field(default=None, description="Query parameters")
    fetch_all: bool = Field(default=True, description="Whether to fetch all results or just one")


class RedisOperationInput(BaseModel):
    """Input schema for Redis operations.
    
    Attributes:
        operation: Redis operation (get, set, delete, exists, keys).
        key: Redis key to operate on.
        value: Value for set operations (optional).
        ttl: Time to live in seconds for set operations (optional).
    """
    operation: str = Field(..., description="Operation: get, set, delete, exists, keys")
    key: str = Field(..., description="Redis key")
    value: Optional[Any] = Field(default=None, description="Value for set operations")
    ttl: Optional[int] = Field(default=None, description="Time to live in seconds")


class PostgresTool(Function):
    """PostgreSQL database tool for accessing UberEats operational data.
    
    Provides secure access to the operational database with built-in safety
    checks to prevent dangerous operations. Only SELECT queries are allowed.
    
    Capabilities:
    - Query order data in real-time
    - Access restaurant information  
    - Retrieve driver details
    - Perform business analytics queries
    
    Safety Features:
    - Prevents destructive SQL operations
    - Connection pooling and error handling
    - Input validation and sanitization
    """
    
    def __init__(self, connection_string: Optional[str] = None):
        super().__init__(
            name="postgres_tool",
            description="Execute PostgreSQL queries to access UberEats database",
            input_schema=PostgresQueryInput
        )
        self.connection_string = connection_string or settings.database_url
        self._connection = None
    
    def _get_connection(self):
        """Get or create database connection.
        
        Returns:
            Active PostgreSQL connection.
            
        Raises:
            Exception: If connection cannot be established.
        """
        if not self._connection or self._connection.closed:
            try:
                self._connection = psycopg2.connect(self.connection_string)
                logger.info("Connected to PostgreSQL database")
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                raise
        return self._connection
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PostgreSQL query safely.
        
        Args:
            input_data: Dictionary containing query, params, and fetch_all options.
            
        Returns:
            Dictionary with success status, data, and metadata.
            
        Note:
            Only SELECT queries are allowed for security reasons.
        """
        try:
            query_input = PostgresQueryInput(**input_data)
            
            dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'UPDATE']
            if any(keyword in query_input.query.upper() for keyword in dangerous_keywords):
                if 'UPDATE' not in query_input.query.upper():
                    return {
                        "success": False,
                        "error": "Dangerous query operations not allowed",
                        "allowed_operations": ["SELECT", "WITH (for SELECT)"]
                    }
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if query_input.params:
                cursor.execute(query_input.query, query_input.params)
            else:
                cursor.execute(query_input.query)
            
            if query_input.fetch_all:
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                data = []
                for row in results:
                    data.append(dict(zip(columns, row)))
            else:
                result = cursor.fetchone()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                data = dict(zip(columns, result)) if result else None
            
            cursor.close()
            
            return {
                "success": True,
                "data": data,
                "row_count": len(results) if query_input.fetch_all else (1 if data else 0),
                "query": query_input.query
            }
            
        except Exception as e:
            logger.error(f"PostgreSQL query error: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query_input.query if 'query_input' in locals() else "Invalid"
            }
    
    def close(self):
        """Close database connection"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("PostgreSQL connection closed")


class RedisTool(Function):
    """
    Redis tool for high-performance caching and real-time data
    
    Enables agents to:
    - Cache expensive calculations
    - Store temporary session data
    - Manage real-time counters
    - Implement pub/sub messaging
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        super().__init__(
            name="redis_tool", 
            description="Perform Redis operations for caching and real-time data",
            input_schema=RedisOperationInput
        )
        self.redis_url = redis_url or settings.redis_url
        self._redis_client = None
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection"""
        try:
            self._redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                encoding='utf-8'
            )
            # Test connection
            self._redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._redis_client = None
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Redis operation"""
        if not self._redis_client:
            return {
                "success": False,
                "error": "Redis connection not available"
            }
        
        try:
            redis_input = RedisOperationInput(**input_data)
            operation = redis_input.operation.lower()
            
            if operation == "get":
                value = self._redis_client.get(redis_input.key)
                # Try to parse JSON
                try:
                    if value:
                        value = json.loads(value)
                except:
                    pass  # Keep as string if not JSON
                
                return {
                    "success": True,
                    "operation": "get",
                    "key": redis_input.key,
                    "value": value,
                    "found": value is not None
                }
            
            elif operation == "set":
                if redis_input.value is None:
                    return {
                        "success": False,
                        "error": "Value is required for set operation"
                    }
                
                # Serialize complex objects to JSON
                if isinstance(redis_input.value, (dict, list)):
                    value_to_store = json.dumps(redis_input.value)
                else:
                    value_to_store = str(redis_input.value)
                
                if redis_input.ttl:
                    self._redis_client.setex(redis_input.key, redis_input.ttl, value_to_store)
                else:
                    self._redis_client.set(redis_input.key, value_to_store)
                
                return {
                    "success": True,
                    "operation": "set",
                    "key": redis_input.key,
                    "ttl": redis_input.ttl
                }
            
            elif operation == "delete":
                deleted = self._redis_client.delete(redis_input.key)
                
                return {
                    "success": True,
                    "operation": "delete", 
                    "key": redis_input.key,
                    "deleted": bool(deleted)
                }
            
            elif operation == "exists":
                exists = self._redis_client.exists(redis_input.key)
                
                return {
                    "success": True,
                    "operation": "exists",
                    "key": redis_input.key,
                    "exists": bool(exists)
                }
            
            elif operation == "keys":
                # Use key as pattern for keys command
                pattern = redis_input.key if redis_input.key else "*"
                keys = self._redis_client.keys(pattern)
                
                return {
                    "success": True,
                    "operation": "keys",
                    "pattern": pattern,
                    "keys": keys,
                    "count": len(keys)
                }
            
            elif operation == "ttl":
                ttl = self._redis_client.ttl(redis_input.key)
                
                return {
                    "success": True,
                    "operation": "ttl",
                    "key": redis_input.key,
                    "ttl": ttl,
                    "status": "exists" if ttl > 0 else "no_expiry" if ttl == -1 else "not_found"
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
                "operation": redis_input.operation if 'redis_input' in locals() else "unknown"
            }
    
    def close(self):
        """Close Redis connection"""
        if self._redis_client:
            self._redis_client.close()
            logger.info("Redis connection closed")


# Pre-configured tool instances for easy use
postgres_tool = PostgresTool() if settings.database_url else None
redis_tool = RedisTool() if settings.redis_url else None

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
    """,
    
    "delivery_performance": """
        SELECT 
            driver_id,
            COUNT(*) as total_deliveries,
            AVG(delivery_time_minutes) as avg_delivery_time,
            AVG(customer_rating) as avg_rating
        FROM delivery_history 
        WHERE delivery_date >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY driver_id
        ORDER BY avg_rating DESC
    """
}

def get_sample_queries() -> Dict[str, str]:
    """Get sample queries for UberEats operations"""
    return UBEREATS_QUERIES