"""
Database connection management for the Abandoned Order Detection System.
Provides connection pooling and utility functions for PostgreSQL operations.
"""

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from dotenv import load_dotenv
from psycopg2 import extras, pool
from psycopg2.extensions import connection as PGConnection

load_dotenv()
logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Manages PostgreSQL connection pool and provides utility methods."""
    
    _instance = None
    _connection_pool = None
    
    def __new__(cls):
        """Singleton pattern to ensure single connection pool."""
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the database connection pool."""
        if self._connection_pool is None:
            self._initialize_pool()
    
    def _initialize_pool(self):
        """Create the connection pool."""
        try:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL not found in environment variables")
            
            pool_size = int(os.getenv("DATABASE_POOL_SIZE", 5))
            max_overflow = int(os.getenv("DATABASE_MAX_OVERFLOW", 10))
            
            self._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=pool_size + max_overflow,
                dsn=database_url
            )
            
            logger.info(f"Database connection pool created with size {pool_size}")
            
        except Exception as e:
            logger.error(f"Failed to create connection pool: {str(e)}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool using context manager.
        
        Automatically returns connection to pool when done.
        """
        connection = None
        try:
            connection = self._connection_pool.getconn()
            yield connection
        finally:
            if connection:
                self._connection_pool.putconn(connection)
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> None:
        """Execute a query that doesn't return results (INSERT, UPDATE, DELETE).
        
        Args:
            query: SQL query to execute
            params: Query parameters for safe parameterized queries
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
    
    def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """Execute a query and fetch a single row as a dictionary.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Dictionary containing the row data, or None if no results
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                return dict(result) if result else None
    
    def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute a query and fetch all rows as a list of dictionaries.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            List of dictionaries containing row data
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
    
    def insert_returning(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """Execute an INSERT query with RETURNING clause.
        
        Args:
            query: INSERT query with RETURNING clause
            params: Query parameters
            
        Returns:
            Dictionary containing the returned row data
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                conn.commit()
                return dict(result) if result else None
    
    def close_pool(self):
        """Close all connections in the pool."""
        if self._connection_pool:
            self._connection_pool.closeall()
            logger.info("Database connection pool closed")

# Convenience functions for direct use
_db_connection = None

def get_connection_pool() -> DatabaseConnection:
    """Get the singleton database connection pool instance."""
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
    return _db_connection

@contextmanager
def get_connection():
    """Get a database connection from the pool."""
    pool = get_connection_pool()
    with pool.get_connection() as conn:
        yield conn

def execute_query(query: str, params: Optional[Tuple] = None) -> None:
    """Execute a query without returning results."""
    pool = get_connection_pool()
    pool.execute_query(query, params)

def fetch_one(query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
    """Fetch a single row from the database."""
    pool = get_connection_pool()
    return pool.fetch_one(query, params)

def fetch_all(query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
    """Fetch all rows from the database."""
    pool = get_connection_pool()
    return pool.fetch_all(query, params)

def test_connection() -> bool:
    """Test the database connection.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        result = fetch_one("SELECT 1 as test")
        return result is not None and result.get('test') == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False

def get_problematic_orders(threshold_minutes: int = 30) -> List[Dict[str, Any]]:
    """Get orders that may need cancellation review.
    
    Args:
        threshold_minutes: Minimum age of order to consider problematic
        
    Returns:
        List of problematic orders with driver and timing information
    """
    query = """
        SELECT 
            o.id,
            o.order_number,
            o.status,
            o.driver_id,
            d.name as driver_name,
            d.status as driver_status,
            d.last_movement,
            d.current_lat as driver_lat,
            d.current_lng as driver_lng,
            o.delivery_lat,
            o.delivery_lng,
            EXTRACT(EPOCH FROM (NOW() - d.last_movement))/60 as minutes_since_movement,
            o.estimated_delivery_time,
            EXTRACT(EPOCH FROM (NOW() - o.estimated_delivery_time))/60 as minutes_overdue,
            EXTRACT(EPOCH FROM (NOW() - o.created_at))/60 as order_age_minutes
        FROM orders o
        LEFT JOIN drivers d ON o.driver_id = d.id
        WHERE o.status = 'out_for_delivery'
        AND o.created_at < NOW() - make_interval(mins => %s)
        AND NOT EXISTS (
            SELECT 1 FROM cancellations c WHERE c.order_id = o.id
        )
        ORDER BY o.created_at ASC
    """
    return fetch_all(query, (threshold_minutes,))

def log_order_event(order_id: int, event_type: str, event_data: Dict[str, Any], 
                   agent_involved: Optional[str] = None) -> None:
    """Log an event in the order's lifecycle.
    
    Args:
        order_id: ID of the order
        event_type: Type of event (e.g., 'analysis_started', 'cancellation_decided')
        event_data: JSON data associated with the event
        agent_involved: Name of the CrewAI agent involved
    """
    query = """
        INSERT INTO order_events (order_id, event_type, event_data, agent_involved, timestamp)
        VALUES (%s, %s, %s, %s, NOW())
    """
    import json
    execute_query(query, (order_id, event_type, json.dumps(event_data), agent_involved))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if test_connection():
        print("✅ Database connection successful!")
        
        orders = get_problematic_orders()
        print(f"Found {len(orders)} problematic orders")
    else:
        print("❌ Database connection failed!")