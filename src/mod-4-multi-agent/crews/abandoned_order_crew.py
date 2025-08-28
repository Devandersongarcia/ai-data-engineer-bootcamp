"""
CrewAI crew implementation for monitoring and handling abandoned orders.
Integrates with Langfuse for comprehensive observability.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

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

def initialize_observability() -> Optional[Langfuse]:
    """Initialize Langfuse and OpenLit for observability.
    
    Returns:
        Langfuse client instance or None if initialization fails
    """
    try:
        openlit.init(
            application_name="abandoned-order-detection",
            environment=os.getenv("ENVIRONMENT", "development"),
            otlp_endpoint=os.getenv("OTLP_ENDPOINT", None),
        )
        
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        )
        
        logger.info("Observability initialized with Langfuse and OpenLit")
        return langfuse
        
    except Exception as e:
        logger.warning(f"Failed to initialize observability: {str(e)}. Continuing without monitoring.")
        return None

@CrewBase
class AbandonedOrderCrew:
    """Crew for monitoring and handling abandoned orders.
    
    Uses an orchestrator-worker pattern with three specialized agents.
    Provides comprehensive order analysis and decision-making capabilities.
    """
    
    agents_config = '../config/agents.yaml'
    tasks_config = '../config/tasks.yaml'
    
    def __init__(self) -> None:
        """Initialize the crew with tools and observability."""
        self.order_query_tool = OrderQueryTool()
        self.driver_status_tool = DriverStatusTool()
        self.time_analysis_tool = TimeAnalysisTool()
        self.order_update_tool = OrderUpdateTool()
        self.notification_tool = NotificationTool()
        
        self.langfuse = initialize_observability()
        self.analysis_results: Dict[int, Dict[str, Any]] = {}
    
    @agent
    def order_guardian(self) -> Agent:
        """Create the Order Guardian agent - the orchestrator and decision maker.
        
        This agent coordinates the analysis and makes final cancellation decisions.
        
        Returns:
            Configured Agent instance for order guardianship
        """
        return Agent(
            config=self.agents_config['order_guardian'],
            tools=[
                self.order_query_tool,
                self.order_update_tool,
                self.notification_tool
            ],
            llm=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"),
            max_rpm=int(os.getenv("CREW_MAX_RPM", 10)),
            memory=os.getenv("CREW_MEMORY_ENABLED", "true").lower() == "true",
            verbose=os.getenv("CREW_VERBOSE", "true").lower() == "true",
            allow_delegation=True,
            reasoning=True,
            max_reasoning_attempts=2
        )
    
    @agent
    def delivery_tracker(self) -> Agent:
        """Create the Delivery Tracker agent - GPS and driver movement specialist.
        
        This agent analyzes driver behavior and movement patterns.
        
        Returns:
            Configured Agent instance for delivery tracking
        """
        return Agent(
            config=self.agents_config['delivery_tracker'],
            tools=[
                self.order_query_tool,
                self.driver_status_tool
            ],
            llm=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"),
            max_rpm=int(os.getenv("CREW_MAX_RPM", 10)),
            verbose=os.getenv("CREW_VERBOSE", "true").lower() == "true"
        )
    
    @agent
    def timeline_analyzer(self) -> Agent:
        """Create the Timeline Analyzer agent - SLA and time metrics specialist.
        
        This agent evaluates delivery timelines and SLA compliance.
        
        Returns:
            Configured Agent instance for timeline analysis
        """
        return Agent(
            config=self.agents_config['timeline_analyzer'],
            tools=[
                self.order_query_tool,
                self.time_analysis_tool
            ],
            llm=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"),
            max_rpm=int(os.getenv("CREW_MAX_RPM", 10)),
            verbose=os.getenv("CREW_VERBOSE", "true").lower() == "true"
        )
    
    @task
    def driver_analysis_task(self) -> Task:
        """Task for analyzing driver status and movement.
        
        Assigned to the Delivery Tracker agent.
        
        Returns:
            Configured Task instance for driver analysis
        """
        return Task(
            config=self.tasks_config['driver_analysis'],
            agent=self.delivery_tracker(),
            output_file='output/driver_analysis.json'
        )
    
    @task
    def timeline_analysis_task(self) -> Task:
        """Task for analyzing order timeline and SLA compliance.
        
        Assigned to the Timeline Analyzer agent.
        
        Returns:
            Configured Task instance for timeline analysis
        """
        return Task(
            config=self.tasks_config['timeline_analysis'],
            agent=self.timeline_analyzer(),
            output_file='output/timeline_analysis.json'
        )
    
    @task
    def cancellation_decision_task(self) -> Task:
        """Task for making the final cancellation decision.
        
        Assigned to the Order Guardian agent.
        Uses context from both analysis tasks.
        
        Returns:
            Configured Task instance for cancellation decisions
        """
        return Task(
            config=self.tasks_config['cancellation_decision'],
            agent=self.order_guardian(),
            context=[
                self.driver_analysis_task(),
                self.timeline_analysis_task()
            ],
            output_file='output/cancellation_decision.json'
        )
    
    @crew
    def crew(self) -> Crew:
        """Assemble the crew with all agents and tasks.
        
        Configured for sequential processing with monitoring.
        
        Returns:
            Configured Crew instance ready for execution
        """
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            memory=os.getenv("CREW_MEMORY_ENABLED", "true").lower() == "true",
            verbose=os.getenv("CREW_VERBOSE", "true").lower() == "true",
            max_rpm=int(os.getenv("CREW_MAX_RPM", 10)),
            planning=os.getenv("CREW_PLANNING_ENABLED", "true").lower() == "true",
            planning_llm=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
        )
    
    def analyze_order(self, order_id: int) -> Dict[str, Any]:
        """Analyze a potentially abandoned order.
        
        Args:
            order_id: The ID of the order to analyze
            
        Returns:
            Dictionary containing the analysis results and decision
        """
        try:
            span = self._start_analysis_trace(order_id)
            
            log_order_event(order_id, "analysis_started", {
                "crew": "abandoned_order_crew",
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"Starting analysis for order {order_id}")
            
            result = self.crew().kickoff(inputs={'order_id': order_id})
            result_data = self._parse_crew_result(result)
            
            self._log_to_langfuse(span, result_data)
            
            log_order_event(order_id, "analysis_completed", {
                "crew": "abandoned_order_crew",
                "decision": result_data.get('decision', 'unknown'),
                "confidence_score": result_data.get('confidence_score', 0),
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"Analysis complete for order {order_id}: {result_data.get('decision', 'unknown')}")
            
            return result_data
            
        except Exception as e:
            logger.error(f"Error analyzing order {order_id}: {str(e)}")
            
            log_order_event(order_id, "analysis_error", {
                "crew": "abandoned_order_crew",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
            self._log_error_to_langfuse(order_id, e)
            
            return {
                "error": str(e),
                "decision": "ERROR",
                "order_id": order_id
            }
    
    def _start_analysis_trace(self, order_id: int) -> Optional[Any]:
        """Start Langfuse trace for order analysis.
        
        Args:
            order_id: Order ID being analyzed
            
        Returns:
            Langfuse span object or None if tracing unavailable
        """
        if not self.langfuse:
            return None
            
        try:
            return self.langfuse.span(
                name=f"analyze_order_{order_id}",
                metadata={
                    "order_id": order_id,
                    "timestamp": datetime.now().isoformat(),
                    "environment": os.getenv("ENVIRONMENT", "development")
                },
                input={"order_id": order_id}
            )
        except Exception as e:
            logger.warning(f"Could not start Langfuse trace: {e}")
            return None
    
    def _parse_crew_result(self, result: Any) -> Dict[str, Any]:
        """Parse crew execution result into dictionary.
        
        Args:
            result: Raw result from crew execution
            
        Returns:
            Parsed result dictionary
        """
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"raw_output": result}
        elif hasattr(result, 'raw'):
            try:
                return json.loads(result.raw)
            except (json.JSONDecodeError, TypeError):
                return {"raw_output": str(result.raw)}
        else:
            return {"raw_output": str(result)}
    
    def _log_to_langfuse(self, span: Optional[Any], result_data: Dict[str, Any]) -> None:
        """Log analysis results to Langfuse.
        
        Args:
            span: Langfuse span object
            result_data: Analysis results to log
        """
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
                    trace_id=span.trace_id if hasattr(span, 'trace_id') else None,
                    name="decision_confidence",
                    value=confidence,
                    comment=f"Decision: {result_data.get('decision', 'unknown')}"
                )
            
            span.end()
        except Exception as e:
            logger.warning(f"Could not update Langfuse trace: {e}")
    
    def _log_error_to_langfuse(self, order_id: int, error: Exception) -> None:
        """Log error to Langfuse.
        
        Args:
            order_id: Order ID that failed analysis
            error: Exception that occurred
        """
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
    
    def batch_analyze_orders(self, order_ids: list[int]) -> Dict[int, Dict[str, Any]]:
        """Analyze multiple orders in batch.
        
        Args:
            order_ids: List of order IDs to analyze
            
        Returns:
            Dictionary mapping order IDs to their analysis results
        """
        results = {}
        
        for order_id in order_ids:
            logger.info(f"Analyzing order {order_id} in batch")
            results[order_id] = self.analyze_order(order_id)
        
        self._log_batch_analysis(order_ids, results)
        return results
    
    def _log_batch_analysis(self, order_ids: list[int], results: Dict[int, Dict[str, Any]]) -> None:
        """Log batch analysis results to Langfuse.
        
        Args:
            order_ids: List of analyzed order IDs
            results: Analysis results for each order
        """
        if not self.langfuse:
            return
            
        try:
            batch_span = self.langfuse.span(
                name="batch_analysis",
                metadata={
                    "total_orders": len(order_ids),
                    "successful": sum(1 for r in results.values() if r.get('decision') != 'ERROR'),
                    "timestamp": datetime.now().isoformat()
                },
                output={"order_ids": order_ids, "summary": {
                    "cancelled": sum(1 for r in results.values() if r.get('decision') == 'CANCEL'),
                    "continued": sum(1 for r in results.values() if r.get('decision') == 'CONTINUE'),
                    "errors": sum(1 for r in results.values() if r.get('decision') == 'ERROR')
                }}
            )
            batch_span.end()
        except Exception as e:
            logger.warning(f"Could not log batch analysis to Langfuse: {e}")

def test_crew() -> Dict[str, Any]:
    """Test the crew with a sample order ID.
    
    Returns:
        Analysis result dictionary
    """
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