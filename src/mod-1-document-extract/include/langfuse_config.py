"""LangFuse configuration and integration module.

Provides enterprise-grade LLM observability through:
- Centralized prompt management with versioning
- Performance metrics and cost tracking
- Quality evaluation and annotation queues
- Custom decorators for enhanced observability
"""
import os
from typing import Dict, Any, Optional
from functools import wraps
import time
from datetime import datetime
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
from dotenv import load_dotenv

load_dotenv()

class LangFuseManager:
    """Manages LangFuse integration for prompt versioning and observability.
    
    What: Provides centralized access to LangFuse features.
    Why: Enables prompt management and observability without code changes.
    How: Wraps LangFuse SDK with caching and fallback mechanisms.
    
    Implements singleton pattern to maintain single client connection.
    """
    
    def __init__(self):
        self.client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        )
        self._prompt_cache = {}
        self.metrics = {
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "accuracy_scores": []
        }
    
    def get_prompt(
        self, 
        name: str, 
        version: Optional[int] = None,
        label: Optional[str] = "production"
    ) -> Any:
        """Fetch prompt with caching and automatic fallback.
        
        What: Retrieves versioned prompts from LangFuse.
        Why: Enables prompt updates without code deployment.
        How: Caches prompts for 5 minutes, falls back to local YAML if unavailable.
        
        Args:
            name: Prompt identifier
            version: Specific version number (optional)
            label: Deployment label (production, staging, etc.)
            
        Returns:
            Prompt configuration object or local fallback
        """
        cache_key = f"{name}:{label}:{version}"
        
        cached = self._get_cached_prompt(cache_key)
        if cached:
            return cached
        
        try:
            prompt = self.client.get_prompt(
                name=name,
                version=version,
                label=label,
                cache_ttl_seconds=300
            )
            self._cache_prompt(cache_key, prompt)
            return prompt
        except Exception as e:
            return self._get_fallback_prompt(name, e)
    
    def _get_cached_prompt(self, cache_key: str) -> Optional[Any]:
        """Retrieve prompt from cache if still valid."""
        if cache_key in self._prompt_cache:
            age = time.time() - self._prompt_cache[cache_key]["timestamp"]
            if age < 300:
                return self._prompt_cache[cache_key]["prompt"]
        return None
    
    def _cache_prompt(self, cache_key: str, prompt: Any) -> None:
        """Store prompt in cache with timestamp."""
        self._prompt_cache[cache_key] = {
            "prompt": prompt,
            "timestamp": time.time()
        }
    
    def _get_fallback_prompt(self, name: str, error: Exception) -> Dict[str, Any]:
        """Load prompt from local config as fallback."""
        print(f"LangFuse unavailable, using local config: {error}")
        from config import config
        return config.load_yaml("prompts").get(name.replace("-", "_"), {})
    
    def log_extraction_quality(
        self,
        trace_id: str,
        model_id: str,
        confidence: float,
        extraction_time: float,
        token_count: int,
        cost: float
    ):
        """Log comprehensive extraction quality metrics.
        
        What: Records extraction performance and quality metrics.
        Why: Enables data-driven optimization of prompts and models.
        How: Sends scores to LangFuse and updates local metrics.
        """
        metrics = [
            ("extraction_quality", confidence, f"Model: {model_id}, Time: {extraction_time}s"),
            ("cost_efficiency", cost, None)
        ]
        
        for name, value, comment in metrics:
            self.client.score(
                trace_id=trace_id,
                name=name,
                value=value,
                data_type="NUMERIC",
                comment=comment
            )
        
        self._update_metrics(token_count, cost, confidence)
    
    def evaluate_extraction(
        self,
        trace_id: str,
        expected: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> float:
        """
        Run LLM-as-judge evaluation on extraction quality.
        Returns accuracy score 0-1.
        """
        evaluation_prompt = self.get_prompt("extraction-evaluator")

        score = self.client.evaluate(
            trace_id=trace_id,
            input={
                "expected": expected,
                "actual": actual
            },
            evaluator_prompt=evaluation_prompt,
            name="extraction_accuracy"
        )
        
        return score.value if score else 0.0
    
    def create_annotation_queue(
        self,
        name: str,
        description: str,
        filters: Dict[str, Any]
    ):
        """Create annotation queue for manual review."""
        return self.client.create_annotation_queue(
            name=name,
            description=description,
            filters=filters
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        avg_accuracy = (
            sum(self.metrics["accuracy_scores"]) / len(self.metrics["accuracy_scores"])
            if self.metrics["accuracy_scores"] else 0
        )
        
        return {
            "total_processed": self.metrics["total_calls"],
            "total_tokens": self.metrics["total_tokens"],
            "total_cost": round(self.metrics["total_cost"], 2),
            "average_accuracy": round(avg_accuracy, 3),
            "timestamp": datetime.now().isoformat()
        }

def with_observability(
    name: str,
    capture_input: bool = True,
    capture_output: bool = True,
    metadata: Optional[Dict[str, Any]] = None
):
    """Enhanced decorator combining LangFuse observability with metrics.
    
    What: Wraps functions with automatic tracing and error handling.
    Why: Provides consistent observability across all DAG tasks.
    How: Uses LangFuse's observe decorator with additional metadata tracking.
    
    Args:
        name: Observation name for tracing
        capture_input: Whether to log function inputs
        capture_output: Whether to log function outputs
        metadata: Additional metadata to attach
    """
    def decorator(func):
        @wraps(func)
        @observe(
            name=name,
            capture_input=capture_input,
            capture_output=capture_output,
            as_type="task"
        )
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            if metadata:
                langfuse_context.update_current_observation(metadata=metadata)
            
            try:
                result = func(*args, **kwargs)
                _log_execution_metrics(start_time, "success", metadata)
                return result
            except Exception as e:
                _log_execution_metrics(start_time, "failed", metadata, error=str(e))
                raise
        
        return wrapper
    return decorator

def _log_execution_metrics(
    start_time: float, 
    status: str, 
    metadata: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> None:
    """Log execution metrics to current observation."""
    execution_time = time.time() - start_time
    metrics = {
        "execution_time": execution_time,
        "status": status,
        **(metadata or {})
    }
    
    if error:
        metrics["error"] = error
        level = "ERROR"
    else:
        level = None
    
    langfuse_context.update_current_observation(
        metadata=metrics,
        level=level
    )

langfuse_manager = LangFuseManager()