"""CrewAI crew implementation for monitoring and handling abandoned orders."""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Optional

import openlit
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from langfuse import Langfuse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.database_tools import (
    OrderQueryTool,
    DriverStatusTool,
    TimeAnalysisTool,
    OrderUpdateTool,
    NotificationTool
)
from database.connection import log_order_event

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_RPM = 10
DEFAULT_ENVIRONMENT = "development"
LANGFUSE_DEFAULT_HOST = "https://cloud.langfuse.com"
MAX_REASONING_ATTEMPTS = 2


def _get_bool_env(key: str, default: bool = True) -> bool:
    """Get boolean environment variable with default."""
    return os.getenv(key, str(default)).lower() == "true"


def _get_int_env(key: str, default: int) -> int:
    """Get integer environment variable with default."""
    return int(os.getenv(key, default))


def initialize_observability() -> Optional[Langfuse]:
    """Initialize Langfuse and OpenLit for observability."""
    try:
        openlit.init(
            application_name="abandoned-order-detection",
            environment=os.getenv("ENVIRONMENT", DEFAULT_ENVIRONMENT),
            otlp_endpoint=os.getenv("OTLP_ENDPOINT", None),
        )
        
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", LANGFUSE_DEFAULT_HOST)
        )
        
        logger.info("Observability initialized with Langfuse and OpenLit")
        return langfuse
        
    except Exception as e:
        logger.warning(f"Failed to initialize observability: {e}. Continuing without monitoring.")
        return None


@CrewBase
class AbandonedOrderCrew:
    """Multi-agent crew for abandoned order detection and decision-making.
    
    Uses orchestrator-worker pattern with three specialized agents:
    - Order Guardian: Final decision maker and orchestrator
    - Delivery Tracker: GPS and driver movement analysis
    - Timeline Analyzer: SLA compliance and timing evaluation
    """
    
    agents_config = '../config/agents.yaml'
    tasks_config = '../config/tasks.yaml'
    
    def __init__(self) -> None:
        self.order_query_tool = OrderQueryTool()
        self.driver_status_tool = DriverStatusTool()
        self.time_analysis_tool = TimeAnalysisTool()
        self.order_update_tool = OrderUpdateTool()
        self.notification_tool = NotificationTool()
        
        self.langfuse = initialize_observability()
        self.analysis_results: dict[int, dict[str, Any]] = {}
    
    def _create_base_agent_config(self) -> dict[str, Any]:
        """Create base configuration shared by all agents."""
        return {
            "llm": os.getenv("OPENAI_MODEL_NAME", DEFAULT_MODEL),
            "max_rpm": _get_int_env("CREW_MAX_RPM", DEFAULT_MAX_RPM),
            "verbose": _get_bool_env("CREW_VERBOSE"),
        }
    
    @agent
    def order_guardian(self) -> Agent:
        """Orchestrator agent that makes final cancellation decisions."""
        config = self._create_base_agent_config()
        return Agent(
            config=self.agents_config['order_guardian'],
            tools=[self.order_query_tool, self.order_update_tool, self.notification_tool],
            memory=_get_bool_env("CREW_MEMORY_ENABLED"),
            allow_delegation=True,
            reasoning=True,
            max_reasoning_attempts=MAX_REASONING_ATTEMPTS,
            **config
        )
    
    @agent
    def delivery_tracker(self) -> Agent:
        """Specialist in GPS tracking and driver movement patterns."""
        config = self._create_base_agent_config()
        return Agent(
            config=self.agents_config['delivery_tracker'],
            tools=[self.order_query_tool, self.driver_status_tool],
            **config
        )
    
    @agent
    def timeline_analyzer(self) -> Agent:
        """Specialist in SLA compliance and delivery timeline evaluation."""
        config = self._create_base_agent_config()
        return Agent(
            config=self.agents_config['timeline_analyzer'],
            tools=[self.order_query_tool, self.time_analysis_tool],
            **config
        )
    
    @task
    def driver_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['driver_analysis'],
            agent=self.delivery_tracker(),
            output_file='output/driver_analysis.json'
        )
    
    @task
    def timeline_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['timeline_analysis'],
            agent=self.timeline_analyzer(),
            output_file='output/timeline_analysis.json'
        )
    
    @task
    def cancellation_decision_task(self) -> Task:
        """Final decision task using context from both analysis tasks."""
        return Task(
            config=self.tasks_config['cancellation_decision'],
            agent=self.order_guardian(),
            context=[self.driver_analysis_task(), self.timeline_analysis_task()],
            output_file='output/cancellation_decision.json'
        )
    
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            memory=_get_bool_env("CREW_MEMORY_ENABLED"),
            verbose=_get_bool_env("CREW_VERBOSE"),
            max_rpm=_get_int_env("CREW_MAX_RPM", DEFAULT_MAX_RPM),
            planning=_get_bool_env("CREW_PLANNING_ENABLED"),
            planning_llm=os.getenv("OPENAI_MODEL_NAME", DEFAULT_MODEL)
        )
    
    def analyze_order(self, order_id: int) -> dict[str, Any]:
        """Analyze potentially abandoned order and make cancellation decision."""
        try:
            span = self._start_analysis_trace(order_id)
            
            self._log_analysis_event(order_id, "analysis_started")
            logger.info(f"Starting analysis for order {order_id}")
            
            result = self.crew().kickoff(inputs={'order_id': order_id})
            result_data = self._parse_crew_result(result)
            
            self._log_to_langfuse(span, result_data)
            self._log_analysis_event(order_id, "analysis_completed", {
                "decision": result_data.get('decision', 'unknown'),
                "confidence_score": result_data.get('confidence_score', 0)
            })
            
            logger.info(f"Analysis complete for order {order_id}: {result_data.get('decision', 'unknown')}")
            return result_data
            
        except Exception as e:
            return self._handle_analysis_error(order_id, e)
    
    def _log_analysis_event(self, order_id: int, event_type: str, extra_data: dict[str, Any] = None) -> None:
        """Log order analysis event with consistent structure."""
        event_data = {
            "crew": "abandoned_order_crew",
            "timestamp": datetime.now().isoformat()
        }
        if extra_data:
            event_data.update(extra_data)
        
        log_order_event(order_id, event_type, event_data)
    
    def _handle_analysis_error(self, order_id: int, error: Exception) -> dict[str, Any]:
        """Handle and log analysis errors consistently."""
        logger.error(f"Error analyzing order {order_id}: {error}")
        
        self._log_analysis_event(order_id, "analysis_error", {"error": str(error)})
        self._log_error_to_langfuse(order_id, error)
        
        return {
            "error": str(error),
            "decision": "ERROR",
            "order_id": order_id
        }
    
    def _start_analysis_trace(self, order_id: int) -> Optional[Any]:
        """Start Langfuse trace for order analysis."""
        if not self.langfuse:
            return None
            
        try:
            return self.langfuse.span(
                name=f"analyze_order_{order_id}",
                metadata={
                    "order_id": order_id,
                    "timestamp": datetime.now().isoformat(),
                    "environment": os.getenv("ENVIRONMENT", DEFAULT_ENVIRONMENT)
                },
                input={"order_id": order_id}
            )
        except Exception as e:
            logger.warning(f"Could not start Langfuse trace: {e}")
            return None
    
    def _parse_crew_result(self, result: Any) -> dict[str, Any]:
        """Parse crew execution result into structured dictionary."""
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"raw_output": result}
        
        if hasattr(result, 'raw'):
            try:
                return json.loads(result.raw)
            except (json.JSONDecodeError, TypeError):
                return {"raw_output": str(result.raw)}
        
        return {"raw_output": str(result)}
    
    def _log_to_langfuse(self, span: Optional[Any], result_data: dict[str, Any]) -> None:
        """Log analysis results to Langfuse with scoring."""
        if not span or not isinstance(result_data, dict):
            return
            
        try:
            confidence = result_data.get('confidence_score', 0)
            span.update(
                output=result_data,
                metadata={
                    "decision": result_data.get('decision'),
                    "confidence": confidence,
                    "primary_reason": result_data.get('primary_reason')
                }
            )
            
            if hasattr(self.langfuse, 'score'):
                self.langfuse.score(
                    trace_id=getattr(span, 'trace_id', None),
                    name="decision_confidence",
                    value=confidence,
                    comment=f"Decision: {result_data.get('decision', 'unknown')}"
                )
            
            span.end()
        except Exception as e:
            logger.warning(f"Could not update Langfuse trace: {e}")
    
    def _log_error_to_langfuse(self, order_id: int, error: Exception) -> None:
        """Log analysis errors to Langfuse for observability."""
        if not self.langfuse:
            return
            
        try:
            error_span = self.langfuse.span(
                name=f"analyze_order_error_{order_id}",
                metadata={
                    "order_id": order_id,
                    "error": str(error),
                    "timestamp": datetime.now().isoformat()
                },
                level="ERROR"
            )
            error_span.end()
        except Exception as log_error:
            logger.warning(f"Could not log error to Langfuse: {log_error}")
    
    def batch_analyze_orders(self, order_ids: list[int]) -> dict[int, dict[str, Any]]:
        """Analyze multiple orders and provide batch summary."""
        results = {}
        
        for order_id in order_ids:
            logger.info(f"Analyzing order {order_id} in batch")
            results[order_id] = self.analyze_order(order_id)
        
        self._log_batch_summary(order_ids, results)
        return results
    
    def _log_batch_summary(self, order_ids: list[int], results: dict[int, dict[str, Any]]) -> None:
        """Log batch analysis summary to Langfuse."""
        if not self.langfuse:
            return
            
        try:
            decision_counts = self._calculate_decision_summary(results)
            successful_count = sum(1 for r in results.values() if r.get('decision') != 'ERROR')
            
            batch_span = self.langfuse.span(
                name="batch_analysis",
                metadata={
                    "total_orders": len(order_ids),
                    "successful": successful_count,
                    "timestamp": datetime.now().isoformat()
                },
                output={"order_ids": order_ids, "summary": decision_counts}
            )
            batch_span.end()
        except Exception as e:
            logger.warning(f"Could not log batch analysis to Langfuse: {e}")
    
    def _calculate_decision_summary(self, results: dict[int, dict[str, Any]]) -> dict[str, int]:
        """Calculate summary of decisions made across batch analysis."""
        return {
            "cancelled": sum(1 for r in results.values() if r.get('decision') == 'CANCEL'),
            "continued": sum(1 for r in results.values() if r.get('decision') == 'CONTINUE'),
            "errors": sum(1 for r in results.values() if r.get('decision') == 'ERROR')
        }


def test_crew() -> dict[str, Any]:
    """Test the crew with sample order for validation."""
    from dotenv import load_dotenv
    
    load_dotenv()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    crew = AbandonedOrderCrew()
    test_order_id = 1
    
    logger.info(f"Testing crew with order ID: {test_order_id}")
    result = crew.analyze_order(test_order_id)
    
    logger.info("Analysis Result:")
    logger.info(json.dumps(result, indent=2))
    
    return result


if __name__ == "__main__":
    test_crew()