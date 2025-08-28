"""Production-grade connection pooling with comprehensive monitoring.

This module provides advanced connection pooling capabilities for both
relational databases (PostgreSQL) and vector databases (Qdrant) with
extensive metrics collection and health monitoring.
"""

import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, Generator

from qdrant_client import QdrantClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from config.settings import get_settings
from .logging_utils import get_logger
from .performance_utils import PerformanceMetrics, get_performance_monitor


class ConnectionStatus(Enum):
    """Enumeration for connection lifecycle states."""
    ACTIVE = "active"
    IDLE = "idle" 
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class ConnectionMetrics:
    """Comprehensive metrics tracking for database connections.
    
    Attributes:
        created_at: Connection creation timestamp
        last_used: Last activity timestamp
        use_count: Total number of operations performed
        status: Current connection status
        error_count: Number of errors encountered
        total_query_time_ms: Cumulative query execution time
    """
    created_at: datetime
    last_used: datetime
    use_count: int = 0
    status: ConnectionStatus = ConnectionStatus.IDLE
    error_count: int = 0
    total_query_time_ms: float = 0.0
    
    def update_usage(self, query_time_ms: float = 0.0, error: bool = False) -> None:
        """Update metrics after connection usage.
        
        Args:
            query_time_ms: Execution time for the operation
            error: Whether an error occurred during the operation
        """
        self.last_used = datetime.now()
        self.use_count += 1
        self.total_query_time_ms += query_time_ms
        
        if error:
            self.error_count += 1
            self.status = ConnectionStatus.ERROR
        else:
            self.status = ConnectionStatus.ACTIVE
    
    def get_avg_query_time(self) -> float:
        """Calculate average query execution time.
        
        Returns:
            Average query time in milliseconds
        """
        return self.total_query_time_ms / self.use_count if self.use_count > 0 else 0.0
    
    def is_stale(self, max_idle_minutes: int = 30) -> bool:
        """Determine if connection has been idle too long.
        
        Args:
            max_idle_minutes: Maximum allowed idle time
            
        Returns:
            True if connection should be considered stale
        """
        idle_time = datetime.now() - self.last_used
        return idle_time > timedelta(minutes=max_idle_minutes)
    
    def get_error_rate(self) -> float:
        """Calculate error rate for this connection.
        
        Returns:
            Error rate as a percentage (0.0 to 1.0)
        """
        return self.error_count / self.use_count if self.use_count > 0 else 0.0


class DatabaseConnectionPool:
    """Production-grade PostgreSQL connection pool with advanced monitoring.
    
    Features:
        - Optimized connection pooling with SQLAlchemy
        - Real-time metrics collection and monitoring
        - Automatic connection health checks and recovery
        - Comprehensive logging and alerting
        - Thread-safe operations with proper synchronization
    """
    
    def __init__(
        self, 
        database_url: str, 
        pool_size: int = 10, 
        max_overflow: int = 20
    ):
        """Initialize database connection pool with monitoring.
        
        Args:
            database_url: Database connection string
            pool_size: Base number of connections to maintain
            max_overflow: Maximum additional connections allowed
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.logger = get_logger(__name__)
        
        self._connection_metrics: Dict[int, ConnectionMetrics] = {}
        self._lock = threading.RLock()
        
        self.engine = self._create_optimized_engine()
        self._setup_event_listeners()
        
        self.logger.info(f"Database pool initialized: {pool_size}/{max_overflow}")
    
    def _create_optimized_engine(self) -> Engine:
        """Create SQLAlchemy engine with production-optimized settings.
        
        Returns:
            Configured SQLAlchemy engine instance
        """
        settings = get_settings()
        
        engine_config = {
            'poolclass': QueuePool,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_pre_ping': True,
            'pool_recycle': 3600,  # 1 hour
            'pool_timeout': 30,
            'echo': False
        }
        
        # PostgreSQL-specific optimizations
        if 'postgresql' in self.database_url:
            engine_config['connect_args'] = {
                'connect_timeout': getattr(settings, 'connection_timeout', 10),
                'application_name': f"{getattr(settings, 'app_title', 'app')}_pool",
                'options': '-c statement_timeout=120000'  # 2 minutes
            }
        
        return create_engine(self.database_url, **engine_config)
    
    def _setup_event_listeners(self) -> None:
        """Configure SQLAlchemy event listeners for comprehensive monitoring."""
        
        @event.listens_for(self.engine, 'connect')
        def on_connect(dbapi_conn, connection_record):
            """Handle new connection creation."""
            conn_id = id(dbapi_conn)
            with self._lock:
                self._connection_metrics[conn_id] = ConnectionMetrics(
                    created_at=datetime.now(),
                    last_used=datetime.now(),
                    status=ConnectionStatus.ACTIVE
                )
            self.logger.debug(f"Connection created: {conn_id}")
        
        @event.listens_for(self.engine, 'checkout')
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            """Handle connection checkout from pool."""
            conn_id = id(dbapi_conn)
            with self._lock:
                if conn_id in self._connection_metrics:
                    metrics = self._connection_metrics[conn_id]
                    metrics.status = ConnectionStatus.ACTIVE
                    metrics.last_used = datetime.now()
        
        @event.listens_for(self.engine, 'checkin')
        def on_checkin(dbapi_conn, connection_record):
            """Handle connection return to pool."""
            conn_id = id(dbapi_conn)
            with self._lock:
                if conn_id in self._connection_metrics:
                    self._connection_metrics[conn_id].status = ConnectionStatus.IDLE
        
        @event.listens_for(self.engine, 'close')
        def on_close(dbapi_conn, connection_record):
            """Handle connection closure."""
            conn_id = id(dbapi_conn)
            with self._lock:
                if conn_id in self._connection_metrics:
                    self._connection_metrics[conn_id].status = ConnectionStatus.CLOSED
                    # Remove metrics after brief delay for final processing
                    del self._connection_metrics[conn_id]
            self.logger.debug(f"Connection closed: {conn_id}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with comprehensive monitoring and error handling.
        
        Yields:
            Active database connection from the pool
            
        Raises:
            Various database-related exceptions
        """
        start_time = time.time()
        connection = None
        
        try:
            connection = self.engine.connect()
            checkout_time = (time.time() - start_time) * 1000
            
            # Monitor slow connection acquisition
            if checkout_time > 1000:
                self.logger.warning(f"Slow connection checkout: {checkout_time:.1f}ms")
            
            yield connection
            
        except Exception as e:
            self._handle_connection_error(connection, e)
            raise
        finally:
            if connection:
                self._finalize_connection_usage(connection, start_time)
    
    def _handle_connection_error(self, connection, error: Exception) -> None:
        """Handle connection errors and update metrics."""
        if connection:
            conn_id = id(connection.connection)
            with self._lock:
                if conn_id in self._connection_metrics:
                    self._connection_metrics[conn_id].update_usage(error=True)
        
        self.logger.error(f"Database connection error: {error}")
    
    def _finalize_connection_usage(self, connection, start_time: float) -> None:
        """Update connection metrics and close connection properly."""
        query_time_ms = (time.time() - start_time) * 1000
        conn_id = id(connection.connection)
        
        with self._lock:
            if conn_id in self._connection_metrics:
                self._connection_metrics[conn_id].update_usage(query_time_ms)
        
        connection.close()
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get comprehensive pool status and performance metrics.
        
        Returns:
            Dictionary containing detailed pool statistics and health metrics
        """
        pool = self.engine.pool
        
        with self._lock:
            metrics = list(self._connection_metrics.values())
            
            status_counts = {
                ConnectionStatus.ACTIVE: sum(1 for m in metrics if m.status == ConnectionStatus.ACTIVE),
                ConnectionStatus.IDLE: sum(1 for m in metrics if m.status == ConnectionStatus.IDLE),
                ConnectionStatus.ERROR: sum(1 for m in metrics if m.status == ConnectionStatus.ERROR),
                ConnectionStatus.CLOSED: sum(1 for m in metrics if m.status == ConnectionStatus.CLOSED)
            }
            
            total_queries = sum(m.use_count for m in metrics)
            total_errors = sum(m.error_count for m in metrics)
            total_time = sum(m.total_query_time_ms for m in metrics)
        
        pool_stats = {
            'pool_configuration': {
                'pool_size': self.pool_size,
                'max_overflow': self.max_overflow,
                'current_size': pool.size(),
            },
            'connection_status': {
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalid': pool.invalid(),
                'active': status_counts[ConnectionStatus.ACTIVE],
                'idle': status_counts[ConnectionStatus.IDLE],
                'error': status_counts[ConnectionStatus.ERROR]
            },
            'performance_metrics': {
                'total_connections': len(metrics),
                'total_queries': total_queries,
                'total_errors': total_errors,
                'error_rate': total_errors / total_queries if total_queries > 0 else 0.0,
                'avg_query_time_ms': total_time / total_queries if total_queries > 0 else 0.0,
                'pool_utilization': pool.checkedout() / (pool.size() + pool.overflow()) if pool.size() > 0 else 0.0
            },
            'health_indicators': {
                'is_healthy': total_errors / total_queries < 0.05 if total_queries > 0 else True,
                'stale_connections': sum(1 for m in metrics if m.is_stale()),
                'high_error_connections': sum(1 for m in metrics if m.get_error_rate() > 0.1)
            }
        }
        
        return pool_stats
    
    def cleanup_stale_connections(self, max_idle_minutes: int = 30) -> int:
        """Clean up metrics for stale connections.
        
        Args:
            max_idle_minutes: Maximum idle time before considering connection stale
            
        Returns:
            Number of stale connections cleaned up
        """
        with self._lock:
            stale_connections = [
                conn_id for conn_id, metrics in self._connection_metrics.items()
                if metrics.is_stale(max_idle_minutes)
            ]
            
            for conn_id in stale_connections:
                del self._connection_metrics[conn_id]
        
        if stale_connections:
            self.logger.info(f"Cleaned up {len(stale_connections)} stale connections")
        
        return len(stale_connections)
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for the connection pool.
        
        Returns:
            Dictionary with health status and diagnostic information
        """
        health_result = {
            'healthy': False,
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        try:
            # Test basic connectivity
            with self.get_connection() as conn:
                result = conn.execute(text("SELECT 1"))
                connectivity_check = result.fetchone()[0] == 1
                health_result['checks']['connectivity'] = connectivity_check
            
            # Check pool status
            pool_status = self.get_pool_status()
            health_result['checks']['pool_utilization'] = pool_status['performance_metrics']['pool_utilization'] < 0.9
            health_result['checks']['error_rate'] = pool_status['performance_metrics']['error_rate'] < 0.05
            health_result['checks']['stale_connections'] = pool_status['health_indicators']['stale_connections'] < 5
            
            # Overall health assessment
            all_checks_passed = all(health_result['checks'].values())
            health_result['healthy'] = all_checks_passed
            
            if not all_checks_passed:
                self.logger.warning(f"Pool health check issues detected: {health_result['checks']}")
            
        except Exception as e:
            self.logger.error(f"Pool health check failed: {e}")
            health_result['checks']['connectivity'] = False
            health_result['error'] = str(e)
        
        return health_result


class QdrantConnectionPool:
    """Connection pool for Qdrant vector database."""
    
    def __init__(self, url: str, api_key: str, pool_size: int = 5):
        self.url = url
        self.api_key = api_key
        self.pool_size = pool_size
        self.logger = get_logger(__name__)
        self._connections = []
        self._available = threading.Semaphore(pool_size)
        self._lock = threading.RLock()
        
        # Pre-create connections
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool with pre-created connections."""
        self.logger.info(f"Initializing Qdrant connection pool with {self.pool_size} connections")
        
        for i in range(self.pool_size):
            try:
                client = QdrantClient(url=self.url, api_key=self.api_key)
                # Test connection
                client.get_collections()
                self._connections.append(client)
            except Exception as e:
                self.logger.error(f"Failed to create Qdrant connection {i}: {e}")
        
        self.logger.info(f"Successfully created {len(self._connections)} Qdrant connections")
    
    @contextmanager
    def get_connection(self) -> Generator[QdrantClient, None, None]:
        """Get Qdrant connection from pool."""
        self._available.acquire()
        
        try:
            with self._lock:
                if self._connections:
                    client = self._connections.pop()
                else:
                    # Fallback: create new connection
                    client = QdrantClient(url=self.url, api_key=self.api_key)
            
            yield client
            
        except Exception as e:
            self.logger.error(f"Qdrant connection error: {e}")
            # Don't return potentially corrupted connection to pool
            client = None
            raise
        finally:
            with self._lock:
                if client and len(self._connections) < self.pool_size:
                    self._connections.append(client)
            
            self._available.release()
    
    def health_check(self) -> bool:
        """Perform health check on Qdrant connections."""
        try:
            with self.get_connection() as client:
                collections = client.get_collections()
                return isinstance(collections.collections, list)
        except Exception as e:
            self.logger.error(f"Qdrant health check failed: {e}")
            return False
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get Qdrant pool status."""
        with self._lock:
            return {
                'total_connections': len(self._connections),
                'available_connections': len(self._connections),
                'pool_size': self.pool_size
            }


class ConnectionManager:
    """Centralized connection manager for all databases."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._pools: Dict[str, Any] = {}
        self._lock = threading.RLock()
    
    def register_postgresql_pool(self, name: str, database_url: str, **kwargs):
        """Register a PostgreSQL connection pool."""
        with self._lock:
            pool = DatabaseConnectionPool(database_url, **kwargs)
            self._pools[name] = pool
            self.logger.info(f"Registered PostgreSQL pool: {name}")
            return pool
    
    def register_qdrant_pool(self, name: str, url: str, api_key: str, **kwargs):
        """Register a Qdrant connection pool."""
        with self._lock:
            pool = QdrantConnectionPool(url, api_key, **kwargs)
            self._pools[name] = pool
            self.logger.info(f"Registered Qdrant pool: {name}")
            return pool
    
    def get_pool(self, name: str):
        """Get connection pool by name."""
        with self._lock:
            return self._pools.get(name)
    
    def get_all_pool_status(self) -> Dict[str, Any]:
        """Get status of all connection pools."""
        with self._lock:
            return {
                name: pool.get_pool_status() 
                for name, pool in self._pools.items()
            }
    
    def health_check_all(self) -> Dict[str, bool]:
        """Perform health check on all pools."""
        with self._lock:
            return {
                name: pool.health_check()
                for name, pool in self._pools.items()
            }
    
    def cleanup_all(self):
        """Cleanup all connection pools."""
        with self._lock:
            for name, pool in self._pools.items():
                if hasattr(pool, 'cleanup_stale_connections'):
                    pool.cleanup_stale_connections()


# Global connection manager
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get global connection manager instance."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


def setup_default_pools():
    """Setup default connection pools using configuration."""
    settings = get_settings()
    manager = get_connection_manager()
    
    # Setup PostgreSQL pool
    try:
        manager.register_postgresql_pool(
            "default_postgresql",
            settings.database_url,
            pool_size=getattr(settings, 'db_pool_size', 10),
            max_overflow=getattr(settings, 'db_max_overflow', 20)
        )
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to setup PostgreSQL pool: {e}")
    
    # Setup Qdrant pool
    try:
        manager.register_qdrant_pool(
            "default_qdrant",
            settings.qdrant_url,
            settings.qdrant_api_key,
            pool_size=getattr(settings, 'qdrant_pool_size', 5)
        )
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to setup Qdrant pool: {e}")


# Auto-setup pools on module import
try:
    setup_default_pools()
except Exception as e:
    logger = get_logger(__name__)
    logger.warning(f"Could not auto-setup default pools: {e}")