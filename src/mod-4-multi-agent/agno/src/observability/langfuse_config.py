"""
Langfuse configuration and setup for UberEats delivery optimization system
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, timedelta

from langfuse import Langfuse, observe
from langfuse.openai import openai as langfuse_openai
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class LangfuseManager:
    """Centralized Langfuse management for UberEats system with robust fallback mechanisms"""
    
    def __init__(self):
        self.client = None
        self.initialized = False
        self.last_health_check = None
        self.health_check_interval = 300  # 5 minutes
        self.is_healthy = False
        self.connection_retries = 0
        self.max_retries = 3
        self._setup_langfuse()
    
    def _setup_langfuse(self):
        """Initialize Langfuse client with environment configuration"""
        try:
            # Get Langfuse configuration from environment
            secret_key = os.getenv('LANGFUSE_SECRET_KEY')
            public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
            host = os.getenv('LANGFUSE_HOST', 'https://us.cloud.langfuse.com')
            
            if not secret_key or not public_key:
                logger.warning("Langfuse credentials not found. Observability disabled.")
                return
            
            # Initialize Langfuse client
            self.client = Langfuse(
                secret_key=secret_key,
                public_key=public_key,
                host=host,
                debug=False  # Set to True for debugging
            )
            
            # Configure OpenAI with Langfuse tracing
            self._setup_openai_tracing()
            
            # Test connection health
            self._check_langfuse_health()
            
            self.initialized = True
            logger.info(f"Langfuse initialized successfully. Host: {host}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            self.initialized = False
            self.is_healthy = False
    
    def _setup_openai_tracing(self):
        """Configure OpenAI client with Langfuse tracing"""
        try:
            # Replace OpenAI client with Langfuse-instrumented version
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if openai_api_key:
                # This automatically traces OpenAI API calls
                langfuse_openai.api_key = openai_api_key
                logger.info("OpenAI tracing enabled with Langfuse")
        except Exception as e:
            logger.error(f"Failed to setup OpenAI tracing: {e}")
    
    def _check_langfuse_health(self) -> bool:
        """Check if Langfuse service is healthy and accessible"""
        if not self.client:
            return False
        
        now = datetime.now()
        if (self.last_health_check and 
            now - self.last_health_check < timedelta(seconds=self.health_check_interval)):
            return self.is_healthy
        
        try:
            # Try to perform a simple health check operation
            # Note: Using a lightweight operation since health() method may not be available
            test_result = self.client.get_prompts(page=1, limit=1)  # Basic API call
            self.is_healthy = True
            self.connection_retries = 0
            self.last_health_check = now
            logger.debug("Langfuse health check passed")
            return True
        except Exception as e:
            self.connection_retries += 1
            self.is_healthy = False
            self.last_health_check = now
            logger.warning(f"Langfuse health check failed (attempt {self.connection_retries}): {e}")
            
            if self.connection_retries >= self.max_retries:
                logger.error("Langfuse service appears to be offline, switching to fallback mode")
                
            return False
    
    def is_service_healthy(self) -> bool:
        """Public method to check if Langfuse service is available"""
        if not self.initialized:
            return False
        return self._check_langfuse_health()
    
    def create_trace(self, name: str, user_id: Optional[str] = None, 
                    metadata: Optional[Dict[str, Any]] = None,
                    tags: Optional[list] = None) -> Any:
        """Create a new trace for tracking operations"""
        if not self.initialized or not self.is_service_healthy():
            logger.debug(f"Langfuse unavailable, skipping trace creation for: {name}")
            return None
        
        try:
            trace = self.client.trace(
                name=name,
                user_id=user_id,
                metadata=metadata or {},
                tags=tags or []
            )
            return trace
        except Exception as e:
            logger.error(f"Failed to create trace: {e}")
            self.is_healthy = False
            return None
    
    def score_trace(self, trace_id: str, name: str, value: float, 
                   comment: Optional[str] = None):
        """Add a score to a trace for performance tracking"""
        if not self.initialized or not self.is_service_healthy():
            logger.debug(f"Langfuse unavailable, skipping trace scoring for: {trace_id}")
            return
        
        try:
            self.client.score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment
            )
        except Exception as e:
            logger.error(f"Failed to score trace: {e}")
            self.is_healthy = False
    
    def flush(self):
        """Flush all pending observations to Langfuse"""
        if self.initialized:
            self.client.flush()

# Global Langfuse manager instance
langfuse_manager = LangfuseManager()

# Decorator for UberEats-specific observability
def observe_ubereats_operation(
    operation_type: str,
    include_args: bool = True,
    include_result: bool = True,
    capture_metrics: bool = True
):
    """
    Enhanced decorator for UberEats operations with business context
    
    Args:
        operation_type: Type of operation (e.g., 'eta_prediction', 'driver_allocation')
        include_args: Whether to capture function arguments
        include_result: Whether to capture function result
        capture_metrics: Whether to capture custom business metrics
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not langfuse_manager.initialized:
                return func(*args, **kwargs)
            
            # Extract business context from arguments
            business_context = _extract_business_context(operation_type, args, kwargs)
            
            # Use Langfuse observe decorator
            @observe(
                name=f"ubereats_{operation_type}",
                metadata={
                    "operation_type": operation_type,
                    "business_context": business_context,
                    "system": "ubereats_optimization"
                },
                capture_input=include_args,
                capture_output=include_result
            )
            def observed_func(*args, **kwargs):
                result = func(*args, **kwargs)
                
                # Capture business metrics if enabled
                if capture_metrics:
                    _capture_business_metrics(operation_type, args, kwargs, result)
                
                return result
            
            return observed_func(*args, **kwargs)
        
        return wrapper
    return decorator

def _extract_business_context(operation_type: str, args: tuple, kwargs: dict) -> Dict[str, Any]:
    """Extract relevant business context from function arguments"""
    context = {}
    
    if operation_type == "eta_prediction":
        # Extract order/restaurant information
        if args and isinstance(args[0], dict):
            order_data = args[0]
            context.update({
                "restaurant_id": order_data.get("restaurant_id"),
                "order_type": order_data.get("order_type"),
                "distance_km": order_data.get("distance_km")
            })
    
    elif operation_type == "driver_allocation":
        # Extract driver/location information
        if args and isinstance(args[0], dict):
            allocation_data = args[0]
            context.update({
                "driver_count": allocation_data.get("available_drivers"),
                "location": allocation_data.get("pickup_location"),
                "priority": allocation_data.get("priority")
            })
    
    elif operation_type == "database_query":
        # Extract query information
        context.update({
            "query_type": kwargs.get("analysis_type", "simple"),
            "database": "postgresql" if "postgres" in str(kwargs.get("query", "")).lower() else "mongodb"
        })
    
    return context

def _capture_business_metrics(operation_type: str, args: tuple, kwargs: dict, result: Any):
    """Capture UberEats-specific business metrics"""
    try:
        # Note: In the current langfuse version, we'll skip trace context for now
        # This can be enhanced when langfuse_context is available
        if not langfuse_manager.initialized or not langfuse_manager.is_service_healthy():
            return
        
        # Log metrics for monitoring (simplified for now)
        logger.info(f"Business metrics captured for {operation_type}: {result}")
        
        # Future enhancement: Add proper trace scoring when langfuse_context is available
    
    except Exception as e:
        logger.error(f"Failed to capture business metrics: {e}")

@contextmanager
def ubereats_operation_trace(operation_name: str, user_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None):
    """Context manager for tracking UberEats operations"""
    trace = langfuse_manager.create_trace(
        name=f"ubereats_{operation_name}",
        user_id=user_id,
        metadata=metadata,
        tags=["ubereats", "production", operation_name]
    )
    
    try:
        yield trace
    finally:
        if trace:
            langfuse_manager.flush()

# Import the prompt registry
from .prompt_registry import prompt_registry

# Prompt management utilities
class UberEatsPromptManager:
    """Manage prompts for UberEats agents using Langfuse with robust fallback"""
    
    def __init__(self):
        self.client = langfuse_manager.client
        self.registry = prompt_registry
    
    def get_prompt(self, prompt_name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """Retrieve and compile a prompt with comprehensive fallback strategy"""
        
        # Step 1: Try to get from Langfuse if available and healthy
        if langfuse_manager.initialized and langfuse_manager.is_service_healthy():
            try:
                prompt = self.client.get_prompt(prompt_name)
                compiled_prompt = prompt.compile(**variables) if variables else prompt.prompt
                
                # Cache the successful prompt for offline use
                self.registry.cache_prompt(prompt_name, {
                    "prompt": prompt.prompt,
                    "variables": list(variables.keys()) if variables else []
                })
                
                logger.debug(f"Successfully retrieved prompt from Langfuse: {prompt_name}")
                return compiled_prompt
                
            except Exception as e:
                logger.warning(f"Failed to retrieve prompt '{prompt_name}' from Langfuse: {e}")
                # Mark service as unhealthy and continue to fallback
                langfuse_manager.is_healthy = False
        
        # Step 2: Try to get from local cache
        logger.info(f"Using fallback for prompt: {prompt_name}")
        return self._get_fallback_prompt(prompt_name, variables)
    
    def _get_fallback_prompt(self, prompt_name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """Get prompt using the fallback registry system"""
        try:
            # Get prompt data from registry (cache -> default -> basic fallback)
            prompt_data = self.registry.get_prompt_with_fallback(prompt_name)
            prompt_template = prompt_data.get("prompt", "")
            
            # Compile the prompt with variables if provided
            if variables and prompt_template:
                try:
                    return prompt_template.format(**variables)
                except KeyError as e:
                    logger.warning(f"Missing variable {e} for prompt {prompt_name}, using template as-is")
                    return prompt_template
            
            return prompt_template
            
        except Exception as e:
            logger.error(f"Error in fallback prompt retrieval for {prompt_name}: {e}")
            # Ultimate fallback
            return f"You are a helpful AI assistant for UberEats. Please assist with the request."
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get status of prompt caching and fallback system"""
        langfuse_status = {
            "initialized": langfuse_manager.initialized,
            "healthy": langfuse_manager.is_service_healthy() if langfuse_manager.initialized else False,
            "connection_retries": langfuse_manager.connection_retries,
            "last_health_check": langfuse_manager.last_health_check.isoformat() if langfuse_manager.last_health_check else None
        }
        
        cache_status = self.registry.get_cache_status()
        
        return {
            "langfuse": langfuse_status,
            "cache": cache_status,
            "fallback_ready": True
        }
    
    def clear_expired_cache(self):
        """Clear expired prompts from local cache"""
        self.registry.clear_expired_cache()
    
    def force_cache_refresh(self, prompt_name: str):
        """Force refresh a specific prompt from Langfuse to cache"""
        if not langfuse_manager.initialized:
            logger.warning("Cannot refresh cache - Langfuse not initialized")
            return False
        
        try:
            prompt = self.client.get_prompt(prompt_name)
            self.registry.cache_prompt(prompt_name, {
                "prompt": prompt.prompt,
                "variables": []  # Will be determined during compilation
            })
            logger.info(f"Successfully refreshed cache for prompt: {prompt_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh cache for prompt {prompt_name}: {e}")
            return False

# Global prompt manager
prompt_manager = UberEatsPromptManager()

# Utility functions for integration
def initialize_langfuse():
    """Reinitialize Langfuse (useful for testing)"""
    global langfuse_manager
    langfuse_manager = LangfuseManager()

def is_langfuse_enabled() -> bool:
    """Check if Langfuse is properly configured and enabled"""
    return langfuse_manager.initialized

def flush_langfuse():
    """Flush all pending Langfuse observations"""
    langfuse_manager.flush()