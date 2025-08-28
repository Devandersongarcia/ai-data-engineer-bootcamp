"""Langfuse tracing and monitoring service for LLM usage tracking."""

import os
import sys
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from uuid import uuid4
from contextlib import contextmanager

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from langfuse import Langfuse
    from langfuse.callback import CallbackHandler
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None
    CallbackHandler = None

from config.settings import DevSettings
from utils.logging_utils import get_logger

logger = get_logger(__name__)


class LangfuseTracing:
    """Service for tracing and monitoring LLM usage with Langfuse."""
    
    def __init__(self, settings: DevSettings):
        """Initialize Langfuse tracing service."""
        self.settings = settings
        self.enabled = (
            settings.langfuse_enabled and 
            settings.langfuse_tracing_enabled and 
            LANGFUSE_AVAILABLE
        )
        self.client = None
        self.callback_handler = None
        
        if not LANGFUSE_AVAILABLE:
            logger.warning("Langfuse SDK not available for tracing")
            self.enabled = False
            return
            
        if not self.enabled:
            logger.info("Langfuse tracing disabled")
            return
            
        if not settings.langfuse_secret_key or not settings.langfuse_public_key:
            logger.warning("Langfuse credentials not configured. Tracing disabled.")
            self.enabled = False
            return
            
        try:
            self.client = Langfuse(
                secret_key=settings.langfuse_secret_key,
                public_key=settings.langfuse_public_key,
                host=settings.langfuse_host
            )
            
            # Create callback handler for LangChain integration
            self.callback_handler = CallbackHandler(
                secret_key=settings.langfuse_secret_key,
                public_key=settings.langfuse_public_key,
                host=settings.langfuse_host
            )
            
            logger.info("Langfuse tracing initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse tracing: {e}")
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if tracing is enabled and available."""
        return self.enabled and self.client is not None
    
    def get_callback_handler(self) -> Optional[Any]:
        """Get LangChain callback handler for tracing."""
        if not self.is_enabled():
            return None
        return self.callback_handler
    
    @contextmanager
    def trace_session(self, session_name: str, user_id: Optional[str] = None, 
                     metadata: Optional[Dict[str, Any]] = None):
        """Context manager for tracing a complete user session."""
        if not self.is_enabled():
            yield None
            return
            
        session_id = str(uuid4())
        session_metadata = {
            "session_name": session_name,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        try:
            # Start session
            trace = self.client.trace(
                id=session_id,
                name=session_name,
                user_id=user_id,
                metadata=session_metadata
            )
            
            logger.info(f"Started tracing session: {session_name} ({session_id})")
            yield trace
            
        except Exception as e:
            logger.error(f"Error during session tracing: {e}")
            yield None
        finally:
            # Flush any pending traces
            if self.client:
                self.client.flush()
    
    def track_sql_generation(self, 
                           user_question: str,
                           generated_sql: str,
                           success: bool,
                           error_message: Optional[str] = None,
                           execution_time: Optional[float] = None,
                           token_usage: Optional[Dict[str, int]] = None,
                           session_id: Optional[str] = None) -> Optional[str]:
        """Track SQL generation events."""
        if not self.is_enabled():
            return None
            
        try:
            event_id = str(uuid4())
            
            # Create generation event
            generation = self.client.generation(
                id=event_id,
                name="sql_generation",
                input=user_question,
                output=generated_sql if success else error_message,
                model="gpt-3.5-turbo",
                metadata={
                    "success": success,
                    "execution_time_seconds": execution_time,
                    "error": error_message,
                    "prompt_source": "langfuse",
                    "temperature": self.settings.temperature
                },
                usage={
                    "input": token_usage.get("input_tokens", 0) if token_usage else 0,
                    "output": token_usage.get("output_tokens", 0) if token_usage else 0,
                    "total": token_usage.get("total_tokens", 0) if token_usage else 0
                } if token_usage else None,
                trace_id=session_id
            )
            
            logger.debug(f"Tracked SQL generation: {event_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error tracking SQL generation: {e}")
            return None
    
    def track_database_query(self,
                           sql_query: str,
                           success: bool,
                           row_count: Optional[int] = None,
                           execution_time: Optional[float] = None,
                           error_message: Optional[str] = None,
                           session_id: Optional[str] = None) -> Optional[str]:
        """Track database query execution."""
        if not self.is_enabled():
            return None
            
        try:
            event_id = str(uuid4())
            
            span = self.client.span(
                id=event_id,
                name="database_query",
                input=sql_query,
                output=f"Returned {row_count} rows" if success and row_count is not None else error_message,
                metadata={
                    "success": success,
                    "row_count": row_count,
                    "execution_time_seconds": execution_time,
                    "error": error_message,
                    "database_url": self.settings.database_url.split('@')[-1] if '@' in self.settings.database_url else "masked"
                },
                trace_id=session_id
            )
            
            logger.debug(f"Tracked database query: {event_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error tracking database query: {e}")
            return None
    
    def track_user_feedback(self,
                          trace_id: str,
                          score: float,
                          comment: Optional[str] = None) -> bool:
        """Track user feedback for a specific trace."""
        if not self.is_enabled():
            return False
            
        try:
            self.client.score(
                trace_id=trace_id,
                name="user_satisfaction",
                value=score,
                comment=comment
            )
            
            logger.info(f"Tracked user feedback for trace {trace_id}: {score}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking user feedback: {e}")
            return False
    
    def get_usage_stats(self, 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get usage statistics (this would require additional API calls)."""
        # Note: This is a placeholder. Langfuse doesn't have direct API for stats yet.
        # You would typically view these in the dashboard.
        return {
            "message": "Usage stats available in Langfuse dashboard",
            "dashboard_url": f"{self.settings.langfuse_host}/project",
            "tracing_enabled": self.is_enabled()
        }
    
    def flush(self):
        """Flush any pending traces to Langfuse."""
        if self.client:
            try:
                self.client.flush()
                logger.debug("Flushed pending traces to Langfuse")
            except Exception as e:
                logger.error(f"Error flushing traces: {e}")


class TracingMetrics:
    """Helper class for collecting and formatting tracing metrics."""
    
    @staticmethod
    def extract_token_usage(response) -> Optional[Dict[str, int]]:
        """Extract token usage from LLM response."""
        try:
            # For OpenAI responses
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                return {
                    "input_tokens": getattr(usage, 'input_tokens', 0),
                    "output_tokens": getattr(usage, 'output_tokens', 0),
                    "total_tokens": getattr(usage, 'total_tokens', 0)
                }
            elif hasattr(response, 'response_metadata'):
                usage = response.response_metadata.get('token_usage', {})
                return {
                    "input_tokens": usage.get('prompt_tokens', 0),
                    "output_tokens": usage.get('completion_tokens', 0),
                    "total_tokens": usage.get('total_tokens', 0)
                }
        except Exception as e:
            logger.debug(f"Could not extract token usage: {e}")
            
        return None
    
    @staticmethod
    def calculate_estimated_cost(token_usage: Dict[str, int], model: str = "gpt-3.5-turbo") -> Optional[float]:
        """Calculate estimated cost based on token usage."""
        # Pricing as of 2024 (update as needed)
        pricing = {
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},  # per 1K tokens
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03}
        }
        
        if model not in pricing or not token_usage:
            return None
            
        try:
            rates = pricing[model]
            input_cost = (token_usage.get("input_tokens", 0) / 1000) * rates["input"]
            output_cost = (token_usage.get("output_tokens", 0) / 1000) * rates["output"]
            return round(input_cost + output_cost, 6)
        except Exception:
            return None


# Global tracing instance (initialized by the application)
_global_tracer: Optional[LangfuseTracing] = None


def initialize_global_tracer(settings: DevSettings) -> LangfuseTracing:
    """Initialize the global tracing instance."""
    global _global_tracer
    _global_tracer = LangfuseTracing(settings)
    return _global_tracer


def get_global_tracer() -> Optional[LangfuseTracing]:
    """Get the global tracing instance."""
    return _global_tracer