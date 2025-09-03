# src/memory/redis_memory.py - Redis Memory Backend for Agents
import redis
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import asyncio
import hashlib

from ..config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Memory entry structure"""
    key: str
    value: Any
    timestamp: datetime
    ttl: Optional[int] = None
    tags: List[str] = None


class RedisAgentMemory:
    """
    Redis-based memory system for agents with advanced features:
    - Automatic TTL management
    - Memory tagging and categorization
    - Memory search and retrieval
    - Performance optimization
    - Memory analytics
    """
    
    def __init__(self, agent_id: str, redis_url: Optional[str] = None):
        self.agent_id = agent_id
        self.redis_url = redis_url or settings.redis_url
        self.ttl = settings.redis_cache_ttl
        self.key_prefix = f"agent:{agent_id}:"
        
        # Redis client
        self._redis = None
        self._connection_pool = None
        
        # Memory statistics
        self.stats = {
            "total_entries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "memory_usage_bytes": 0
        }
        
        # Initialize connection
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection with error handling"""
        try:
            if not settings.redis_enabled or not self.redis_url:
                logger.warning(f"Redis disabled or URL not provided for agent {self.agent_id}")
                return
            
            # Create connection pool for better performance
            self._connection_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=settings.redis_max_connections,
                decode_responses=True,
                encoding='utf-8'
            )
            
            self._redis = redis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            self._redis.ping()
            logger.info(f"✅ Redis memory initialized for agent {self.agent_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis for agent {self.agent_id}: {e}")
            self._redis = None
    
    def _get_key(self, memory_key: str) -> str:
        """Get full Redis key with prefix"""
        return f"{self.key_prefix}{memory_key}"
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value to JSON string"""
        try:
            if isinstance(value, (dict, list, str, int, float, bool)):
                return json.dumps(value, default=str, ensure_ascii=False)
            else:
                # Handle complex objects
                return json.dumps(str(value), ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Serialization error for {value}: {e}")
            return json.dumps(str(value))
    
    def _deserialize_value(self, serialized: str) -> Any:
        """Deserialize JSON string to value"""
        try:
            return json.loads(serialized)
        except Exception as e:
            logger.warning(f"Deserialization error for {serialized}: {e}")
            return serialized
    
    async def store(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Store value in Redis memory with optional TTL and tags
        
        Args:
            key: Memory key
            value: Value to store
            ttl: Time to live in seconds (uses default if None)
            tags: Optional tags for categorization
        
        Returns:
            True if stored successfully
        """
        if not self._redis:
            logger.warning(f"Redis not available for agent {self.agent_id}")
            return False
        
        try:
            redis_key = self._get_key(key)
            
            # Create memory entry
            memory_entry = MemoryEntry(
                key=key,
                value=value,
                timestamp=datetime.now(),
                ttl=ttl or self.ttl,
                tags=tags or []
            )
            
            # Serialize the entire entry
            serialized_entry = self._serialize_value(asdict(memory_entry))
            
            # Store in Redis with TTL
            effective_ttl = ttl or self.ttl
            if effective_ttl:
                self._redis.setex(redis_key, effective_ttl, serialized_entry)
            else:
                self._redis.set(redis_key, serialized_entry)
            
            # Store tags for searchability
            if tags:
                for tag in tags:
                    tag_key = f"{self.key_prefix}tag:{tag}"
                    self._redis.sadd(tag_key, key)
                    if effective_ttl:
                        self._redis.expire(tag_key, effective_ttl)
            
            # Update statistics
            self.stats["total_entries"] += 1
            
            logger.debug(f"Stored memory: {key} for agent {self.agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing memory {key} for agent {self.agent_id}: {e}")
            return False
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve value from Redis memory
        
        Args:
            key: Memory key to retrieve
            
        Returns:
            Stored value or None if not found
        """
        if not self._redis:
            return None
        
        try:
            redis_key = self._get_key(key)
            serialized_entry = self._redis.get(redis_key)
            
            if serialized_entry is None:
                self.stats["cache_misses"] += 1
                logger.debug(f"Memory miss: {key} for agent {self.agent_id}")
                return None
            
            # Deserialize memory entry
            entry_dict = self._deserialize_value(serialized_entry)
            
            # Extract value from memory entry
            if isinstance(entry_dict, dict) and "value" in entry_dict:
                self.stats["cache_hits"] += 1
                logger.debug(f"Memory hit: {key} for agent {self.agent_id}")
                return entry_dict["value"]
            else:
                # Fallback for simple values
                self.stats["cache_hits"] += 1
                return entry_dict
                
        except Exception as e:
            logger.error(f"Error retrieving memory {key} for agent {self.agent_id}: {e}")
            self.stats["cache_misses"] += 1
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete memory entry"""
        if not self._redis:
            return False
        
        try:
            redis_key = self._get_key(key)
            deleted = self._redis.delete(redis_key)
            
            if deleted:
                logger.debug(f"Deleted memory: {key} for agent {self.agent_id}")
            
            return bool(deleted)
            
        except Exception as e:
            logger.error(f"Error deleting memory {key} for agent {self.agent_id}: {e}")
            return False
    
    async def search_by_tag(self, tag: str) -> List[str]:
        """Search memory keys by tag"""
        if not self._redis:
            return []
        
        try:
            tag_key = f"{self.key_prefix}tag:{tag}"
            keys = self._redis.smembers(tag_key)
            return list(keys) if keys else []
            
        except Exception as e:
            logger.error(f"Error searching by tag {tag} for agent {self.agent_id}: {e}")
            return []
    
    async def get_all_keys(self) -> List[str]:
        """Get all memory keys for this agent"""
        if not self._redis:
            return []
        
        try:
            pattern = f"{self.key_prefix}*"
            keys = self._redis.keys(pattern)
            
            # Remove prefix and filter out tag keys
            agent_keys = []
            for key in keys:
                if not key.startswith(f"{self.key_prefix}tag:"):
                    clean_key = key.replace(self.key_prefix, "")
                    agent_keys.append(clean_key)
            
            return agent_keys
            
        except Exception as e:
            logger.error(f"Error getting all keys for agent {self.agent_id}: {e}")
            return []
    
    async def clear_memory(self) -> bool:
        """Clear all memory for this agent"""
        if not self._redis:
            return False
        
        try:
            pattern = f"{self.key_prefix}*"
            keys = self._redis.keys(pattern)
            
            if keys:
                deleted = self._redis.delete(*keys)
                logger.info(f"Cleared {deleted} memory entries for agent {self.agent_id}")
                
                # Reset stats
                self.stats["total_entries"] = 0
                
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing memory for agent {self.agent_id}: {e}")
            return False
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        if not self._redis:
            return {"error": "Redis not available"}
        
        try:
            # Get memory usage
            keys = await self.get_all_keys()
            total_keys = len(keys)
            
            # Calculate cache hit rate
            total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
            hit_rate = (self.stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "agent_id": self.agent_id,
                "total_keys": total_keys,
                "cache_hit_rate_percent": round(hit_rate, 2),
                "cache_hits": self.stats["cache_hits"],
                "cache_misses": self.stats["cache_misses"],
                "redis_connection": "active" if self._redis else "inactive",
                "default_ttl_seconds": self.ttl
            }
            
        except Exception as e:
            logger.error(f"Error getting memory stats for agent {self.agent_id}: {e}")
            return {"error": str(e)}
    
    async def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """Extend TTL for a memory entry"""
        if not self._redis:
            return False
        
        try:
            redis_key = self._get_key(key)
            current_ttl = self._redis.ttl(redis_key)
            
            if current_ttl > 0:
                new_ttl = current_ttl + additional_seconds
                self._redis.expire(redis_key, new_ttl)
                logger.debug(f"Extended TTL for {key} by {additional_seconds}s")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error extending TTL for {key}: {e}")
            return False
    
    def close(self):
        """Close Redis connection"""
        if self._connection_pool:
            self._connection_pool.disconnect()
            logger.info(f"Closed Redis connection for agent {self.agent_id}")


# Factory function for easy instantiation
def create_agent_memory(agent_id: str, redis_url: Optional[str] = None) -> RedisAgentMemory:
    """
    Factory function to create Redis memory for an agent
    
    Args:
        agent_id: Unique agent identifier
        redis_url: Optional Redis URL (uses settings default if not provided)
    
    Returns:
        RedisAgentMemory instance
    """
    return RedisAgentMemory(agent_id=agent_id, redis_url=redis_url)


# Global memory registry for agent memory management
_memory_registry: Dict[str, RedisAgentMemory] = {}

def get_agent_memory(agent_id: str) -> RedisAgentMemory:
    """
    Get or create Redis memory for an agent (singleton pattern)
    
    Args:
        agent_id: Agent identifier
        
    Returns:
        RedisAgentMemory instance
    """
    if agent_id not in _memory_registry:
        _memory_registry[agent_id] = create_agent_memory(agent_id)
    
    return _memory_registry[agent_id]

def clear_all_agent_memories():
    """Clear all agent memories from registry"""
    for memory in _memory_registry.values():
        memory.close()
    _memory_registry.clear()
    logger.info("Cleared all agent memories from registry")