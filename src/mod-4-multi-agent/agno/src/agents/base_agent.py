"""Modern Agno 1.1+ Base Agent Architecture.

Provides the foundational base agent class with enhanced capabilities including:
- Redis memory management for persistent state
- Langfuse observability integration
- Performance monitoring and metrics collection
- Timeout protection and error handling
- Dynamic prompt management
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools

from ..config.settings import settings
from ..memory.redis_memory import get_agent_memory
from ..observability.langfuse_config import (
    prompt_manager,
    observe_ubereats_operation,
    langfuse_manager
)

logger = logging.getLogger(__name__)

class UberEatsBaseAgent(Agent):
    """Enhanced base agent with Agno 1.1+ full capabilities.
    
    Features ~10,000x performance improvements over previous versions through:
    - Optimized agent initialization
    - Efficient memory management with Redis
    - Streamlined request processing
    - Advanced observability integration
    
    Attributes:
        agent_id: Unique identifier for this agent instance.
        performance_metrics: Runtime performance tracking data.
        redis_memory: Optional Redis-based memory system.
        prompt_manager: Dynamic prompt management system.
    """
    
    def __init__(
        self,
        agent_id: str,
        instructions: str,
        model_name: Optional[str] = None,
        enable_reasoning: bool = True,
        enable_memory: bool = True,
        specialized_tools: Optional[list] = None,
        **kwargs
    ):
        model = self._get_model(model_name or settings.default_model)
        
        tools = []
        if enable_reasoning:
            tools.append(ReasoningTools(add_instructions=True))
        if specialized_tools:
            tools.extend(specialized_tools)
        
        storage = None
        
        memory = None
        self.redis_memory = None
        if enable_memory and settings.redis_enabled:
            try:
                self.redis_memory = get_agent_memory(agent_id)
                logger.info(f"✅ Redis memory initialized for agent {agent_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis memory for {agent_id}: {e}")
                self.redis_memory = None
        
        super().__init__(
            name=agent_id,
            model=model,
            instructions=instructions,
            tools=tools,
            storage=storage,
            memory=memory,
            markdown=True,
            debug_mode=settings.log_level == "DEBUG",
            monitoring=settings.agno_monitoring_enabled,
            **kwargs
        )
        
        self.agent_id = agent_id
        self.performance_metrics = {
            "requests_processed": 0,
            "avg_response_time": 0.0,
            "error_count": 0,
            "last_activity": None,
            "total_response_time": 0.0
        }
        
        self.timeout = settings.agent_timeout
        self.memory_limit_mb = settings.memory_limit_mb
        
        self.prompt_manager = prompt_manager
        
        logger.info(f"UberEatsBaseAgent '{agent_id}' initialized with Agno 1.1+ capabilities and Langfuse integration")
        
    def _get_model(self, model_name: str):
        """Select and configure the appropriate model.
        
        Args:
            model_name: Name of the model to initialize.
            
        Returns:
            Configured model instance (OpenAI or Anthropic).
            
        Raises:
            ValueError: If required API keys are not configured.
        """
        if "claude" in model_name.lower():
            if not settings.anthropic_api_key:
                logger.warning("Anthropic API key not found, falling back to OpenAI")
                model_name = settings.default_model
            else:
                return Claude(
                    id=model_name,
                    api_key=settings.anthropic_api_key
                )
        
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required but not found in configuration")
            
        return OpenAIChat(
            id=model_name,
            api_key=settings.openai_api_key,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature
        )
    
    def get_dynamic_prompt(
        self, 
        prompt_name: str, 
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get a dynamic prompt from Langfuse with fallback support.
        
        Args:
            prompt_name: Name of the prompt template to retrieve.
            variables: Optional variables to substitute in the prompt.
            
        Returns:
            Formatted prompt string with variables substituted.
        """
        try:
            return self.prompt_manager.get_prompt(prompt_name, variables)
        except Exception as e:
            logger.error(f"Error retrieving prompt {prompt_name}: {e}")
            fallback_request = variables.get('request', 'the user request') if variables else 'the user request'
            return f"You are a helpful UberEats AI agent. Please assist with: {fallback_request}"
    
    def update_instructions_from_prompt(
        self, 
        prompt_name: str, 
        variables: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update agent instructions using a dynamic prompt from Langfuse.
        
        Args:
            prompt_name: Name of the prompt template to use.
            variables: Optional variables for prompt substitution.
        """
        try:
            new_instructions = self.get_dynamic_prompt(prompt_name, variables)
            if new_instructions != self.instructions:
                self.instructions = new_instructions
                logger.info(f"Updated instructions for {self.agent_id} from prompt: {prompt_name}")
        except Exception as e:
            logger.error(f"Failed to update instructions for {self.agent_id}: {e}")
    
    def get_prompt_status(self) -> Dict[str, Any]:
        """Get status of prompt management system.
        
        Returns:
            Dictionary containing prompt system status and cache information.
        """
        try:
            return self.prompt_manager.get_cache_status()
        except Exception as e:
            logger.error(f"Error getting prompt status: {e}")
            return {"error": str(e), "fallback_available": True}
    
    @observe_ubereats_operation(
        operation_type="agent_request_processing",
        include_args=True,
        include_result=True,
        capture_metrics=True
    )
    async def process_request_with_metrics(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process request with built-in performance tracking and error handling.
        
        Args:
            request: Dictionary containing the request data to process.
            
        Returns:
            Dictionary containing the response, processing metrics, and status.
            Includes fields: response, processing_time, agent_id, success, timestamp.
        """
        start_time = time.time()
        request_id = f"{self.agent_id}_{int(start_time)}"
        
        try:
            logger.debug(f"Processing request {request_id} for agent {self.agent_id}")
            
            response = await asyncio.wait_for(
                self.arun(str(request)),
                timeout=self.timeout
            )
            
            processing_time = time.time() - start_time
            
            self._update_metrics(processing_time, success=True)
            
            result = {
                "response": response,
                "processing_time": processing_time,
                "agent_id": self.agent_id,
                "request_id": request_id,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Request {request_id} processed successfully in {processing_time:.3f}s")
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Request {request_id} timed out after {self.timeout}s"
            logger.error(error_msg)
            self._update_metrics(0, success=False)
            
            return {
                "error": error_msg,
                "error_type": "timeout",
                "agent_id": self.agent_id,
                "request_id": request_id,
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Error processing request {request_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._update_metrics(processing_time, success=False)
            
            return {
                "error": error_msg,
                "error_type": type(e).__name__,
                "agent_id": self.agent_id,
                "request_id": request_id,
                "success": False,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }
    
    def _update_metrics(self, response_time: float, success: bool = True) -> None:
        """Update agent performance metrics.
        
        Args:
            response_time: Time taken to process the request in seconds.
            success: Whether the request was processed successfully.
        """
        self.performance_metrics["requests_processed"] += 1
        self.performance_metrics["last_activity"] = datetime.now()
        
        if success:
            self.performance_metrics["total_response_time"] += response_time
            self.performance_metrics["avg_response_time"] = (
                self.performance_metrics["total_response_time"] / 
                max(1, self.performance_metrics["requests_processed"] - self.performance_metrics["error_count"])
            )
        else:
            self.performance_metrics["error_count"] += 1
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive agent health and performance status.
        
        Returns:
            Dictionary containing:
            - Agent status (healthy/degraded/unhealthy)
            - Performance metrics (success rate, response times)
            - Capabilities and configuration
            - Timestamp
        """
        total_requests = self.performance_metrics["requests_processed"]
        error_count = self.performance_metrics["error_count"]
        
        success_rate = ((total_requests - error_count) / max(1, total_requests)) * 100
        
        if success_rate >= 95 and self.performance_metrics["avg_response_time"] < 10:
            status = "healthy"
        elif success_rate >= 90 and self.performance_metrics["avg_response_time"] < 30:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "agent_id": self.agent_id,
            "status": status,
            "metrics": {
                **self.performance_metrics,
                "success_rate": success_rate,
                "last_activity": self.performance_metrics["last_activity"].isoformat() if self.performance_metrics["last_activity"] else None
            },
            "capabilities": {
                "model": self.model.__class__.__name__,
                "model_id": getattr(self.model, 'model', 'unknown'),
                "has_memory": self.memory is not None,
                "has_redis_memory": self.redis_memory is not None,
                "has_storage": self.storage is not None,
                "has_reasoning": any("ReasoningTools" in str(tool) for tool in (self.tools or [])),
                "monitoring_enabled": settings.agno_monitoring_enabled,
                "tools_count": len(self.tools) if self.tools else 0
            },
            "configuration": {
                "timeout": self.timeout,
                "memory_limit_mb": self.memory_limit_mb,
                "enable_reasoning": any("ReasoningTools" in str(tool) for tool in (self.tools or [])),
                "enable_memory": self.memory is not None
            },
            "timestamp": datetime.now().isoformat()
        }
    
    
    async def store_memory(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None, 
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Store data in Redis memory with optional TTL and tags
        
        Args:
            key: Memory key
            value: Value to store
            ttl: Time to live in seconds
            tags: Optional tags for categorization
            
        Returns:
            True if stored successfully
        """
        if not self.redis_memory:
            logger.warning(f"Redis memory not available for agent {self.name}")
            return False
        
        try:
            success = await self.redis_memory.store(key, value, ttl, tags)
            if success:
                logger.debug(f"Stored memory key '{key}' for agent {self.name}")
            return success
        except Exception as e:
            logger.error(f"Error storing memory for agent {self.name}: {e}")
            return False
    
    async def retrieve_memory(self, key: str) -> Optional[Any]:
        """
        Retrieve data from Redis memory
        
        Args:
            key: Memory key to retrieve
            
        Returns:
            Stored value or None if not found
        """
        if not self.redis_memory:
            return None
        
        try:
            value = await self.redis_memory.retrieve(key)
            logger.debug(f"Retrieved memory key '{key}' for agent {self.name}: {'found' if value is not None else 'not found'}")
            return value
        except Exception as e:
            logger.error(f"Error retrieving memory for agent {self.name}: {e}")
            return None
    
    async def delete_memory(self, key: str) -> bool:
        """Delete memory entry"""
        if not self.redis_memory:
            return False
        
        try:
            success = await self.redis_memory.delete(key)
            if success:
                logger.debug(f"Deleted memory key '{key}' for agent {self.name}")
            return success
        except Exception as e:
            logger.error(f"Error deleting memory for agent {self.name}: {e}")
            return False
    
    async def search_memory_by_tag(self, tag: str) -> List[str]:
        """Search memory keys by tag"""
        if not self.redis_memory:
            return []
        
        try:
            keys = await self.redis_memory.search_by_tag(tag)
            logger.debug(f"Found {len(keys)} keys with tag '{tag}' for agent {self.name}")
            return keys
        except Exception as e:
            logger.error(f"Error searching memory by tag for agent {self.name}: {e}")
            return []
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        if not self.redis_memory:
            return {"error": "Redis memory not available", "redis_enabled": False}
        
        try:
            stats = await self.redis_memory.get_memory_stats()
            return stats
        except Exception as e:
            logger.error(f"Error getting memory stats for agent {self.name}: {e}")
            return {"error": str(e)}
    
    async def clear_all_memory(self) -> bool:
        """Clear all memory for this agent"""
        if not self.redis_memory:
            return False
        
        try:
            success = await self.redis_memory.clear_memory()
            if success:
                logger.info(f"Cleared all memory for agent {self.name}")
            return success
        except Exception as e:
            logger.error(f"Error clearing memory for agent {self.name}: {e}")
            return False
    
    
    async def store_conversation_context(
        self, 
        conversation_id: str, 
        context: Dict[str, Any],
        ttl: int = 7200  # 2 hours default
    ) -> bool:
        """Store conversation context with automatic expiry"""
        key = f"conversation:{conversation_id}"
        return await self.store_memory(key, context, ttl, ["conversation", "context"])
    
    async def retrieve_conversation_context(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve conversation context"""
        key = f"conversation:{conversation_id}"
        return await self.retrieve_memory(key)
    
    async def store_task_result(
        self, 
        task_id: str, 
        result: Dict[str, Any],
        ttl: int = 86400  # 24 hours default
    ) -> bool:
        """Store task result for future reference"""
        key = f"task_result:{task_id}"
        return await self.store_memory(key, result, ttl, ["task", "result"])
    
    async def retrieve_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve previous task result"""
        key = f"task_result:{task_id}"
        return await self.retrieve_memory(key)
    
    async def store_learning_data(
        self, 
        learning_key: str, 
        data: Dict[str, Any],
        ttl: int = 604800  # 1 week default
    ) -> bool:
        """Store learning data for continuous improvement"""
        key = f"learning:{learning_key}"
        return await self.store_memory(key, data, ttl, ["learning", "improvement"])
    
    async def retrieve_learning_data(self, learning_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve learning data"""
        key = f"learning:{learning_key}"
        return await self.retrieve_memory(key)
    
    async def get_memory_summary(self) -> Dict[str, Any]:
        """Get agent memory summary if memory is enabled"""
        if not self.memory:
            return {"memory_enabled": False}
        
        try:
            # Get recent memories (implementation depends on AgentMemory interface)
            return {
                "memory_enabled": True,
                "agent_id": self.agent_id,
                "memory_status": "active",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting memory summary for {self.agent_id}: {e}")
            return {
                "memory_enabled": True,
                "memory_status": "error",
                "error": str(e)
            }
    
    async def reset_metrics(self) -> None:
        """Reset performance metrics.
        
        Clears all accumulated performance data and resets counters to zero.
        Useful for benchmarking or after system maintenance.
        """
        self.performance_metrics = {
            "requests_processed": 0,
            "avg_response_time": 0.0,
            "error_count": 0,
            "last_activity": None,
            "total_response_time": 0.0
        }
        logger.info(f"Performance metrics reset for agent {self.agent_id}")
    
    def __repr__(self):
        return f"UberEatsBaseAgent(agent_id='{self.agent_id}', model={self.model.__class__.__name__})"