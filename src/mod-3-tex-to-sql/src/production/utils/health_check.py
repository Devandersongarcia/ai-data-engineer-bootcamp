"""Health check utilities for monitoring system components."""

import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from .logging_utils import get_logger
from .error_handling import create_error_context


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    WARNING = "warning" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    component: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    timestamp: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "details": self.details
        }


class HealthChecker:
    """Centralized health checking system."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.checks = {}
    
    def register_check(self, name: str, check_function, timeout: float = 30.0):
        """
        Register a health check function.
        
        Args:
            name: Name of the component to check
            check_function: Function that performs the health check
            timeout: Timeout in seconds for the check
        """
        self.checks[name] = {
            "function": check_function,
            "timeout": timeout
        }
        self.logger.info(f"Registered health check for: {name}")
    
    def check_component(self, component_name: str) -> HealthCheckResult:
        """
        Check health of a specific component.
        
        Args:
            component_name: Name of the component to check
        
        Returns:
            HealthCheckResult for the component
        """
        if component_name not in self.checks:
            return HealthCheckResult(
                component=component_name,
                status=HealthStatus.UNKNOWN,
                message=f"No health check registered for {component_name}"
            )
        
        check_info = self.checks[component_name]
        start_time = time.time()
        
        try:
            self.logger.debug(f"Running health check for {component_name}")
            
            # Execute the health check with timeout
            result = self._execute_with_timeout(
                check_info["function"],
                check_info["timeout"]
            )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # If result is a dict, extract details
            if isinstance(result, dict):
                status = HealthStatus(result.get("status", "healthy"))
                message = result.get("message", f"{component_name} is healthy")
                details = result.get("details")
            elif isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = f"{component_name} is {'healthy' if result else 'unhealthy'}"
                details = None
            else:
                status = HealthStatus.HEALTHY
                message = str(result) if result else f"{component_name} is healthy"
                details = None
            
            return HealthCheckResult(
                component=component_name,
                status=status,
                message=message,
                response_time_ms=response_time,
                details=details
            )
            
        except TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component=component_name,
                status=HealthStatus.UNHEALTHY,
                message=f"{component_name} health check timed out",
                response_time_ms=response_time
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Health check failed for {component_name}: {e}")
            
            return HealthCheckResult(
                component=component_name,
                status=HealthStatus.UNHEALTHY,
                message=f"{component_name} health check failed: {str(e)}",
                response_time_ms=response_time,
                details={"error": str(e)}
            )
    
    def check_all(self) -> Dict[str, HealthCheckResult]:
        """
        Check health of all registered components.
        
        Returns:
            Dictionary mapping component names to their health check results
        """
        results = {}
        
        for component_name in self.checks.keys():
            results[component_name] = self.check_component(component_name)
        
        return results
    
    def get_overall_status(self) -> Dict[str, Any]:
        """
        Get overall system health status.
        
        Returns:
            Dictionary with overall health information
        """
        results = self.check_all()
        
        # Determine overall status
        statuses = [result.status for result in results.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.WARNING in statuses:
            overall_status = HealthStatus.WARNING
        elif HealthStatus.UNKNOWN in statuses:
            overall_status = HealthStatus.UNKNOWN
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Calculate stats
        total_checks = len(results)
        healthy_count = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY)
        unhealthy_count = sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY)
        warning_count = sum(1 for r in results.values() if r.status == HealthStatus.WARNING)
        
        # Average response time
        response_times = [r.response_time_ms for r in results.values() if r.response_time_ms is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_checks": total_checks,
                "healthy": healthy_count,
                "unhealthy": unhealthy_count,
                "warnings": warning_count,
                "average_response_time_ms": avg_response_time
            },
            "components": {name: result.to_dict() for name, result in results.items()}
        }
    
    def _execute_with_timeout(self, func, timeout: float):
        """Execute function with timeout."""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Health check timed out after {timeout} seconds")
        
        # Set timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))
        
        try:
            result = func()
            return result
        finally:
            signal.alarm(0)  # Cancel alarm
            signal.signal(signal.SIGALRM, old_handler)


# Default health checkers for common components
def check_database_connection(engine):
    """Health check for database connection."""
    def _check():
        try:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return {"status": "healthy", "message": "Database connection successful"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Database connection failed: {e}"}
    return _check


def check_openai_api(openai_client, api_key: str):
    """Health check for OpenAI API."""
    def _check():
        try:
            # Try to get models list (lightweight operation)
            response = openai_client.models.list()
            return {
                "status": "healthy", 
                "message": "OpenAI API connection successful",
                "details": {"models_available": len(response.data) if hasattr(response, 'data') else 0}
            }
        except Exception as e:
            return {"status": "unhealthy", "message": f"OpenAI API connection failed: {e}"}
    return _check


def check_qdrant_connection(qdrant_client):
    """Health check for Qdrant connection."""
    def _check():
        try:
            collections = qdrant_client.get_collections()
            return {
                "status": "healthy",
                "message": "Qdrant connection successful",
                "details": {"collections_count": len(collections.collections)}
            }
        except Exception as e:
            return {"status": "unhealthy", "message": f"Qdrant connection failed: {e}"}
    return _check


def create_default_health_checker() -> HealthChecker:
    """Create health checker with default checks."""
    return HealthChecker()


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker
    
    if _health_checker is None:
        _health_checker = create_default_health_checker()
    
    return _health_checker