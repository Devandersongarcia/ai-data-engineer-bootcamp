"""
Connection pooling utilities for improved performance and resource management
Provides thread-safe connection pools and session management
"""

import time
import threading
import logging
from typing import Dict, Optional, Any
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.constants import AppConfig, APIConstants

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Thread-safe connection pool for HTTP sessions"""
    
    def __init__(
        self,
        pool_size: int = None,
        max_size: int = None,
        keep_alive: int = None,
        block: bool = None
    ):
        """
        Initialize connection pool
        
        Args:
            pool_size: Maximum connections per pool (default from config)
            max_size: Maximum total connections (default from config)  
            keep_alive: Keep-alive timeout in seconds (default from config)
            block: Whether to block when pool is exhausted (default from config)
        """
        self.pool_size = pool_size or AppConfig.CONNECTION_POOL_SIZE
        self.max_size = max_size or AppConfig.CONNECTION_POOL_MAXSIZE
        self.keep_alive = keep_alive or AppConfig.CONNECTION_KEEP_ALIVE
        self.block = block if block is not None else AppConfig.CONNECTION_POOL_BLOCK
        
        # Thread-safe session storage
        self._sessions: Dict[str, requests.Session] = {}
        self._session_timestamps: Dict[str, float] = {}
        self._lock = threading.RLock()
        
        # Pool statistics
        self._stats = {
            'sessions_created': 0,
            'sessions_reused': 0,
            'sessions_expired': 0,
            'pool_hits': 0,
            'pool_misses': 0
        }
        
        logger.info(f"ConnectionPool initialized: {self.pool_size} pool size, {self.max_size} max size")
    
    def _create_session(self, base_url: str) -> requests.Session:
        """Create a new HTTP session with optimized settings"""
        session = requests.Session()
        
        # Configure connection pooling at urllib3 level
        adapter = HTTPAdapter(
            pool_connections=self.pool_size,
            pool_maxsize=self.max_size,
            pool_block=self.block,
            max_retries=0  # We handle retries at a higher level
        )
        
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        # Set default headers
        session.headers.update({
            'User-Agent': 'MindsDB-Client/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Connection': 'keep-alive',
            'Keep-Alive': f'timeout={self.keep_alive}'
        })
        
        # Set default timeout
        session.timeout = APIConstants.DEFAULT_TIMEOUT
        
        self._stats['sessions_created'] += 1
        logger.debug(f"Created new session for {base_url}")
        
        return session
    
    def _get_base_url(self, url: str) -> str:
        """Extract base URL for session key"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def _is_session_expired(self, base_url: str) -> bool:
        """Check if a cached session has expired"""
        if base_url not in self._session_timestamps:
            return True
        
        age = time.time() - self._session_timestamps[base_url]
        return age > self.keep_alive
    
    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions from the pool"""
        current_time = time.time()
        expired_urls = []
        
        for base_url, timestamp in self._session_timestamps.items():
            if current_time - timestamp > self.keep_alive:
                expired_urls.append(base_url)
        
        for base_url in expired_urls:
            if base_url in self._sessions:
                self._sessions[base_url].close()
                del self._sessions[base_url]
                del self._session_timestamps[base_url]
                self._stats['sessions_expired'] += 1
                logger.debug(f"Expired session for {base_url}")
    
    def get_session(self, url: str) -> requests.Session:
        """
        Get a pooled session for the given URL
        
        Args:
            url: Target URL to get session for
            
        Returns:
            requests.Session: Cached or new session
        """
        base_url = self._get_base_url(url)
        
        with self._lock:
            # Clean up expired sessions periodically
            self._cleanup_expired_sessions()
            
            # Check if we have a cached session
            if base_url in self._sessions and not self._is_session_expired(base_url):
                self._stats['pool_hits'] += 1
                self._stats['sessions_reused'] += 1
                logger.debug(f"Reusing cached session for {base_url}")
                return self._sessions[base_url]
            
            # Create new session
            self._stats['pool_misses'] += 1
            session = self._create_session(base_url)
            
            # Cache the session
            if base_url in self._sessions:
                # Close old session if replacing
                self._sessions[base_url].close()
            
            self._sessions[base_url] = session
            self._session_timestamps[base_url] = time.time()
            
            return session
    
    def close_session(self, url: str) -> None:
        """
        Close and remove a session from the pool
        
        Args:
            url: URL whose session to close
        """
        base_url = self._get_base_url(url)
        
        with self._lock:
            if base_url in self._sessions:
                self._sessions[base_url].close()
                del self._sessions[base_url]
                del self._session_timestamps[base_url]
                logger.debug(f"Closed session for {base_url}")
    
    def close_all(self) -> None:
        """Close all pooled sessions"""
        with self._lock:
            for session in self._sessions.values():
                session.close()
            
            self._sessions.clear()
            self._session_timestamps.clear()
            logger.info("Closed all pooled sessions")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            return {
                **self._stats.copy(),
                'active_sessions': len(self._sessions),
                'pool_size': self.pool_size,
                'max_size': self.max_size,
                'keep_alive': self.keep_alive,
                'hit_rate': self._stats['pool_hits'] / max(self._stats['pool_hits'] + self._stats['pool_misses'], 1) * 100
            }
    
    def __del__(self):
        """Cleanup when pool is garbage collected"""
        try:
            self.close_all()
        except:
            pass  # Ignore errors during cleanup


# Global connection pool instance
_global_pool: Optional[ConnectionPool] = None
_global_pool_lock = threading.Lock()


def get_connection_pool() -> ConnectionPool:
    """Get the global connection pool instance (singleton)"""
    global _global_pool
    
    if _global_pool is None:
        with _global_pool_lock:
            if _global_pool is None:
                _global_pool = ConnectionPool()
                logger.info("Global connection pool created")
    
    return _global_pool


def create_pooled_session(url: str = None) -> requests.Session:
    """
    Create or get a pooled session for the given URL
    
    Args:
        url: Target URL (optional, uses dummy URL if not provided)
        
    Returns:
        requests.Session: Pooled session
    """
    if url is None:
        url = "http://localhost"  # Dummy URL for generic sessions
    
    pool = get_connection_pool()
    return pool.get_session(url)


def close_pooled_session(url: str) -> None:
    """
    Close a specific pooled session
    
    Args:
        url: URL whose session to close
    """
    pool = get_connection_pool()
    pool.close_session(url)


def get_pool_stats() -> Dict[str, Any]:
    """Get global connection pool statistics"""
    pool = get_connection_pool()
    return pool.get_stats()


def cleanup_connection_pool() -> None:
    """Cleanup the global connection pool"""
    global _global_pool
    
    with _global_pool_lock:
        if _global_pool is not None:
            _global_pool.close_all()
            _global_pool = None
            logger.info("Global connection pool cleaned up")


class PooledSession:
    """Context manager for pooled sessions"""
    
    def __init__(self, url: str):
        self.url = url
        self.session = None
    
    def __enter__(self) -> requests.Session:
        self.session = create_pooled_session(self.url)
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Don't close the session, keep it in the pool
        pass


# Enhanced session creation with connection pooling
def create_resilient_pooled_session(base_url: str = None) -> requests.Session:
    """
    Create a resilient session with connection pooling support
    
    Args:
        base_url: Base URL for the session
        
    Returns:
        requests.Session: Pooled and resilient session
    """
    # Get pooled session
    session = create_pooled_session(base_url) if base_url else requests.Session()
    
    # If we created a new session (not from pool), configure it
    if base_url is None:
        # Configure connection pooling at urllib3 level
        adapter = HTTPAdapter(
            pool_connections=AppConfig.CONNECTION_POOL_SIZE,
            pool_maxsize=AppConfig.CONNECTION_POOL_MAXSIZE,
            pool_block=AppConfig.CONNECTION_POOL_BLOCK
        )
        
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        # Set default headers
        session.headers.update({
            'User-Agent': 'MindsDB-Client/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Set default timeout
        session.timeout = APIConstants.DEFAULT_TIMEOUT
    
    return session