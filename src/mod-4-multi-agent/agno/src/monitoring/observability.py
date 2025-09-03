# src/monitoring/observability.py - Comprehensive Monitoring and Observability
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import json
import psutil
import time

from prometheus_client import (
    Counter, Histogram, Gauge, CollectorRegistry, 
    start_http_server, generate_latest
)
import structlog
from opentelemetry import trace, metrics as otel_metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from ..config.settings import settings

# Structured logging setup
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

@dataclass
class AgentPerformanceMetrics:
    """Comprehensive agent performance metrics"""
    agent_id: str
    requests_processed: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    total_response_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_activity: Optional[datetime] = None
    error_rate: float = 0.0
    throughput_per_minute: float = 0.0
    
    @property
    def success_rate(self) -> float:
        if self.requests_processed == 0:
            return 100.0
        return (self.successful_requests / self.requests_processed) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['last_activity'] = self.last_activity.isoformat() if self.last_activity else None
        data['success_rate'] = self.success_rate
        return data

@dataclass
class WorkflowMetrics:
    """Comprehensive workflow execution metrics"""
    workflow_id: str
    workflow_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    state_transitions: List[Dict[str, Any]] = None
    quality_score: float = 0.0
    agents_involved: List[str] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.state_transitions is None:
            self.state_transitions = []
        if self.agents_involved is None:
            self.agents_involved = []

class UberEatsMonitoringSystem:
    """Enterprise-grade monitoring and observability system for UberEats agents"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self.setup_prometheus_metrics()
        self.setup_opentelemetry()
        
        # Performance tracking
        self.agent_metrics: Dict[str, AgentPerformanceMetrics] = {}
        self.workflow_metrics: Dict[str, WorkflowMetrics] = {}
        self.system_alerts: List[Dict[str, Any]] = []
        
        # Monitoring configuration
        self.monitoring_active = True
        self.health_check_interval = 30  # seconds
        self.metrics_collection_interval = 10  # seconds
        self.alert_thresholds = {
            "error_rate": 5.0,  # %
            "response_time": 30.0,  # seconds
            "memory_usage": 85.0,  # %
            "cpu_usage": 80.0  # %
        }
        
        # Performance baselines
        self.performance_baselines = {
            "agent_response_time": 2.0,  # Expected < 2s with Agno 1.1+
            "workflow_execution_time": 10.0,  # Expected < 10s
            "system_health_score": 0.95  # Expected > 95%
        }
        
        logger.info("UberEats monitoring system initialized with enhanced observability")
        
    def setup_prometheus_metrics(self):
        """Setup comprehensive Prometheus metrics"""
        
        # Agent-specific metrics
        self.agent_requests_total = Counter(
            'ubereats_agent_requests_total',
            'Total agent requests processed',
            ['agent_id', 'status', 'priority'],
            registry=self.registry
        )
        
        self.agent_response_time = Histogram(
            'ubereats_agent_response_time_seconds',
            'Agent response time distribution',
            ['agent_id', 'agent_type'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.agent_memory_usage = Gauge(
            'ubereats_agent_memory_usage_bytes',
            'Agent memory usage in bytes',
            ['agent_id'],
            registry=self.registry
        )
        
        self.agent_cpu_usage = Gauge(
            'ubereats_agent_cpu_usage_percent',
            'Agent CPU usage percentage',
            ['agent_id'],
            registry=self.registry
        )
        
        # Workflow-specific metrics
        self.workflow_executions_total = Counter(
            'ubereats_workflow_executions_total',
            'Total workflow executions',
            ['workflow_type', 'status', 'complexity'],
            registry=self.registry
        )
        
        self.workflow_execution_time = Histogram(
            'ubereats_workflow_execution_time_seconds',
            'Workflow execution time distribution',
            ['workflow_type'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0],
            registry=self.registry
        )
        
        self.workflow_quality_score = Histogram(
            'ubereats_workflow_quality_score',
            'Workflow quality score distribution',
            ['workflow_type'],
            buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99, 1.0],
            registry=self.registry
        )
        
        self.active_workflows = Gauge(
            'ubereats_active_workflows',
            'Number of currently active workflows',
            registry=self.registry
        )
        
        # System-level metrics
        self.system_health_score = Gauge(
            'ubereats_system_health_score',
            'Overall system health score (0-1)',
            registry=self.registry
        )
        
        self.database_connection_pool = Gauge(
            'ubereats_database_connections',
            'Active database connections',
            ['database_type', 'status'],
            registry=self.registry
        )
        
        self.api_requests_total = Counter(
            'ubereats_api_requests_total',
            'Total API requests',
            ['endpoint', 'method', 'status_code'],
            registry=self.registry
        )
        
        self.api_response_time = Histogram(
            'ubereats_api_response_time_seconds',
            'API response time distribution',
            ['endpoint'],
            registry=self.registry
        )
        
        # Agent Team collaboration metrics
        self.team_collaboration_requests = Counter(
            'ubereats_team_collaboration_requests_total',
            'Agent team collaboration requests',
            ['collaboration_type', 'agents_involved', 'status'],
            registry=self.registry
        )
        
        self.team_coordination_time = Histogram(
            'ubereats_team_coordination_time_seconds',
            'Time spent on agent team coordination',
            ['team_size'],
            registry=self.registry
        )
        
        # Quality and error metrics
        self.quality_validation_score = Histogram(
            'ubereats_quality_validation_score',
            'Quality validation scores',
            ['validation_type'],
            registry=self.registry
        )
        
        self.error_recovery_attempts = Counter(
            'ubereats_error_recovery_attempts_total',
            'Error recovery attempts',
            ['error_type', 'recovery_status'],
            registry=self.registry
        )
        
    def setup_opentelemetry(self):
        """Setup OpenTelemetry for distributed tracing"""
        
        try:
            # Initialize tracer
            self.tracer = trace.get_tracer(__name__, version=settings.api_version)
            
            # Initialize meter with Prometheus reader
            meter_provider = MeterProvider(
                metric_readers=[PrometheusMetricReader()]
            )
            self.meter = meter_provider.get_meter(__name__, version=settings.api_version)
            
            logger.info("OpenTelemetry initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize OpenTelemetry: {e}")
            self.tracer = None
            self.meter = None
    
    async def start_monitoring(self):
        """Start all monitoring tasks"""
        
        logger.info("🚀 Starting comprehensive monitoring system")
        
        # Start Prometheus metrics server if enabled
        if settings.enable_monitoring:
            try:
                start_http_server(9090, registry=self.registry)
                logger.info("📊 Prometheus metrics server started on port 9090")
            except Exception as e:
                logger.warning(f"Failed to start Prometheus server: {e}")
        
        # Start background monitoring tasks
        monitoring_tasks = [
            asyncio.create_task(self.collect_system_metrics()),
            asyncio.create_task(self.monitor_agent_health()),
            asyncio.create_task(self.monitor_workflow_performance()),
            asyncio.create_task(self.detect_anomalies()),
            asyncio.create_task(self.cleanup_old_metrics()),
            asyncio.create_task(self.generate_performance_reports())
        ]
        
        try:
            await asyncio.gather(*monitoring_tasks, return_exceptions=True)
        except Exception as e:
            logger.error("Critical error in monitoring system", error=str(e))
    
    async def collect_system_metrics(self):
        """Collect comprehensive system-level metrics"""
        
        while self.monitoring_active:
            try:
                # System resource metrics
                memory_info = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=1)
                disk_usage = psutil.disk_usage('/')
                
                # Update system health score
                health_score = self.calculate_system_health()
                self.system_health_score.set(health_score)
                
                # Log system metrics with structured logging
                logger.info(
                    "System metrics collected",
                    memory_used_percent=memory_info.percent,
                    memory_available_gb=memory_info.available / (1024**3),
                    cpu_usage_percent=cpu_percent,
                    disk_used_percent=disk_usage.percent,
                    health_score=health_score,
                    active_agents=len(self.agent_metrics),
                    active_workflows=len([w for w in self.workflow_metrics.values() if w.end_time is None])
                )
                
                # Check for system-level alerts
                if memory_info.percent > self.alert_thresholds["memory_usage"]:
                    await self.create_alert(
                        f"High system memory usage: {memory_info.percent:.1f}%",
                        "critical",
                        {"memory_percent": memory_info.percent}
                    )
                
                if cpu_percent > self.alert_thresholds["cpu_usage"]:
                    await self.create_alert(
                        f"High CPU usage: {cpu_percent:.1f}%",
                        "warning",
                        {"cpu_percent": cpu_percent}
                    )
                
                await asyncio.sleep(self.metrics_collection_interval)
                
            except Exception as e:
                logger.error("Error collecting system metrics", error=str(e))
                await asyncio.sleep(self.metrics_collection_interval)
    
    async def monitor_agent_health(self):
        """Monitor individual agent health and performance"""
        
        while self.monitoring_active:
            try:
                unhealthy_agents = []
                
                for agent_id, metrics in self.agent_metrics.items():
                    # Update Prometheus metrics
                    self.agent_memory_usage.labels(agent_id=agent_id).set(
                        metrics.memory_usage_mb * 1024 * 1024
                    )
                    self.agent_cpu_usage.labels(agent_id=agent_id).set(metrics.cpu_usage_percent)
                    
                    # Health checks
                    if metrics.requests_processed > 0:
                        error_rate = (metrics.failed_requests / metrics.requests_processed) * 100
                        
                        if error_rate > self.alert_thresholds["error_rate"]:
                            unhealthy_agents.append(agent_id)
                            await self.create_alert(
                                f"High error rate for agent {agent_id}: {error_rate:.1f}%",
                                "critical",
                                {
                                    "agent_id": agent_id,
                                    "error_rate": error_rate,
                                    "requests_processed": metrics.requests_processed
                                }
                            )
                        
                        if metrics.avg_response_time > self.alert_thresholds["response_time"]:
                            await self.create_alert(
                                f"Slow response time for agent {agent_id}: {metrics.avg_response_time:.2f}s",
                                "warning",
                                {
                                    "agent_id": agent_id,
                                    "avg_response_time": metrics.avg_response_time
                                }
                            )
                    
                    # Performance baseline comparison
                    if metrics.avg_response_time > self.performance_baselines["agent_response_time"]:
                        logger.warning(
                            "Agent performance below baseline",
                            agent_id=agent_id,
                            actual_time=metrics.avg_response_time,
                            baseline=self.performance_baselines["agent_response_time"]
                        )
                    
                    logger.debug(
                        "Agent health monitored",
                        agent_id=agent_id,
                        success_rate=metrics.success_rate,
                        avg_response_time=metrics.avg_response_time,
                        requests_processed=metrics.requests_processed
                    )
                
                # Overall agent health summary
                if unhealthy_agents:
                    logger.warning(
                        "Unhealthy agents detected",
                        unhealthy_count=len(unhealthy_agents),
                        total_agents=len(self.agent_metrics),
                        unhealthy_agents=unhealthy_agents
                    )
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error("Error monitoring agent health", error=str(e))
                await asyncio.sleep(self.health_check_interval)
    
    async def monitor_workflow_performance(self):
        """Monitor workflow execution performance and quality"""
        
        while self.monitoring_active:
            try:
                active_workflows = 0
                slow_workflows = []
                
                for workflow_id, workflow_data in self.workflow_metrics.items():
                    if workflow_data.end_time is None:
                        active_workflows += 1
                        
                        # Check for stuck workflows
                        execution_time = (datetime.now() - workflow_data.start_time).total_seconds()
                        if execution_time > 600:  # 10 minutes
                            slow_workflows.append((workflow_id, execution_time))
                            await self.create_alert(
                                f"Long-running workflow detected: {workflow_id}",
                                "warning",
                                {
                                    "workflow_id": workflow_id,
                                    "execution_time": execution_time,
                                    "workflow_type": workflow_data.workflow_type
                                }
                            )
                    else:
                        # Completed workflow analysis
                        if workflow_data.execution_time > self.performance_baselines["workflow_execution_time"]:
                            logger.info(
                                "Slow workflow completed",
                                workflow_id=workflow_id,
                                execution_time=workflow_data.execution_time,
                                baseline=self.performance_baselines["workflow_execution_time"]
                            )
                        
                        # Quality score analysis
                        if workflow_data.quality_score < 0.9:
                            logger.warning(
                                "Low quality workflow result",
                                workflow_id=workflow_id,
                                quality_score=workflow_data.quality_score,
                                workflow_type=workflow_data.workflow_type
                            )
                
                # Update active workflows gauge
                self.active_workflows.set(active_workflows)
                
                logger.debug(
                    "Workflow performance monitored",
                    active_workflows=active_workflows,
                    slow_workflows_count=len(slow_workflows),
                    total_workflows=len(self.workflow_metrics)
                )
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error("Error monitoring workflow performance", error=str(e))
                await asyncio.sleep(self.health_check_interval)
    
    async def detect_anomalies(self):
        """Detect system anomalies and performance degradation"""
        
        while self.monitoring_active:
            try:
                anomalies_detected = []
                
                # Agent performance anomaly detection
                for agent_id, metrics in self.agent_metrics.items():
                    if metrics.requests_processed < 10:
                        continue  # Not enough data
                    
                    # Response time anomaly
                    if metrics.max_response_time > 5 * metrics.avg_response_time:
                        anomalies_detected.append({
                            "type": "response_time_spike",
                            "agent_id": agent_id,
                            "max_time": metrics.max_response_time,
                            "avg_time": metrics.avg_response_time
                        })
                    
                    # Throughput anomaly
                    current_time = datetime.now()
                    if metrics.last_activity and metrics.last_activity < current_time - timedelta(minutes=30):
                        anomalies_detected.append({
                            "type": "agent_inactive",
                            "agent_id": agent_id,
                            "last_activity": metrics.last_activity.isoformat()
                        })
                
                # System-level anomaly detection
                system_health = self.calculate_system_health()
                if system_health < self.performance_baselines["system_health_score"]:
                    anomalies_detected.append({
                        "type": "system_health_degradation",
                        "current_score": system_health,
                        "baseline": self.performance_baselines["system_health_score"]
                    })
                
                # Report anomalies
                if anomalies_detected:
                    logger.warning(
                        "System anomalies detected",
                        anomaly_count=len(anomalies_detected),
                        anomalies=anomalies_detected
                    )
                    
                    for anomaly in anomalies_detected:
                        await self.create_alert(
                            f"Anomaly detected: {anomaly['type']}",
                            "warning",
                            anomaly
                        )
                
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                logger.error("Error in anomaly detection", error=str(e))
                await asyncio.sleep(120)
    
    async def cleanup_old_metrics(self):
        """Clean up old metrics data to prevent memory bloat"""
        
        while self.monitoring_active:
            try:
                # Clean up old workflow metrics (keep last 24 hours)
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                workflows_to_remove = [
                    wf_id for wf_id, wf_data in self.workflow_metrics.items()
                    if wf_data.end_time and wf_data.end_time < cutoff_time
                ]
                
                for wf_id in workflows_to_remove:
                    del self.workflow_metrics[wf_id]
                
                # Clean up old alerts (keep last 200)
                if len(self.system_alerts) > 200:
                    self.system_alerts = self.system_alerts[-200:]
                
                # Reset agent metrics that haven't been active (keep performance baselines)
                inactive_threshold = datetime.now() - timedelta(hours=6)
                for agent_id, metrics in list(self.agent_metrics.items()):
                    if metrics.last_activity and metrics.last_activity < inactive_threshold:
                        # Reset but keep the agent registered
                        self.agent_metrics[agent_id] = AgentPerformanceMetrics(agent_id=agent_id)
                
                logger.debug(
                    "Metrics cleanup completed",
                    workflows_removed=len(workflows_to_remove),
                    alerts_count=len(self.system_alerts),
                    active_agents=len(self.agent_metrics)
                )
                
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                logger.error("Error in metrics cleanup", error=str(e))
                await asyncio.sleep(3600)
    
    async def generate_performance_reports(self):
        """Generate periodic performance reports"""
        
        while self.monitoring_active:
            try:
                # Generate hourly performance summary
                report = {
                    "timestamp": datetime.now().isoformat(),
                    "system_health_score": self.calculate_system_health(),
                    "agent_performance": {
                        agent_id: {
                            "success_rate": metrics.success_rate,
                            "avg_response_time": metrics.avg_response_time,
                            "requests_processed": metrics.requests_processed
                        }
                        for agent_id, metrics in self.agent_metrics.items()
                    },
                    "workflow_performance": {
                        "total_workflows": len(self.workflow_metrics),
                        "active_workflows": len([w for w in self.workflow_metrics.values() if w.end_time is None]),
                        "avg_execution_time": self._calculate_avg_workflow_time(),
                        "avg_quality_score": self._calculate_avg_quality_score()
                    },
                    "recent_alerts": len(self.system_alerts[-10:])
                }
                
                logger.info("Performance report generated", **report)
                
                await asyncio.sleep(3600)  # Generate reports every hour
                
            except Exception as e:
                logger.error("Error generating performance report", error=str(e))
                await asyncio.sleep(3600)
    
    def calculate_system_health(self) -> float:
        """Calculate overall system health score (0.0 to 1.0)"""
        
        try:
            health_factors = []
            
            # Agent health factor
            if self.agent_metrics:
                agent_success_rates = [
                    metrics.success_rate for metrics in self.agent_metrics.values()
                    if metrics.requests_processed > 0
                ]
                if agent_success_rates:
                    avg_success_rate = sum(agent_success_rates) / len(agent_success_rates)
                    health_factors.append(avg_success_rate / 100)
                else:
                    health_factors.append(1.0)
            else:
                health_factors.append(1.0)
            
            # System resource health factor
            try:
                memory_usage = psutil.virtual_memory().percent
                memory_health = max(0, (100 - memory_usage) / 100)
                health_factors.append(memory_health)
                
                cpu_usage = psutil.cpu_percent()
                cpu_health = max(0, (100 - cpu_usage) / 100)
                health_factors.append(cpu_health)
            except Exception:
                health_factors.append(0.8)  # Default moderate health if can't measure
            
            # Error rate health factor
            total_requests = sum(metrics.requests_processed for metrics in self.agent_metrics.values())
            total_errors = sum(metrics.failed_requests for metrics in self.agent_metrics.values())
            
            if total_requests > 0:
                error_rate = total_errors / total_requests
                error_health = max(0, 1 - error_rate)
                health_factors.append(error_health)
            else:
                health_factors.append(1.0)
            
            # Workflow quality factor
            avg_quality = self._calculate_avg_quality_score()
            if avg_quality > 0:
                health_factors.append(avg_quality)
            
            # Calculate weighted average
            return sum(health_factors) / len(health_factors) if health_factors else 0.5
            
        except Exception as e:
            logger.error("Error calculating system health", error=str(e))
            return 0.5  # Default moderate health on error
    
    def _calculate_avg_workflow_time(self) -> float:
        """Calculate average workflow execution time"""
        completed_workflows = [
            w.execution_time for w in self.workflow_metrics.values() 
            if w.end_time is not None and w.execution_time > 0
        ]
        return sum(completed_workflows) / len(completed_workflows) if completed_workflows else 0.0
    
    def _calculate_avg_quality_score(self) -> float:
        """Calculate average workflow quality score"""
        quality_scores = [
            w.quality_score for w in self.workflow_metrics.values() 
            if w.quality_score > 0
        ]
        return sum(quality_scores) / len(quality_scores) if quality_scores else 0.95
    
    async def create_alert(self, message: str, severity: str = "info", metadata: Dict[str, Any] = None):
        """Create and log system alert"""
        
        alert = {
            "id": f"alert_{int(time.time() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "severity": severity,
            "metadata": metadata or {},
            "acknowledged": False
        }
        
        self.system_alerts.append(alert)
        
        # Log alert with appropriate level
        if severity == "critical":
            logger.error("🚨 Critical alert", **alert)
        elif severity == "warning":
            logger.warning("⚠️ Warning alert", **alert)
        else:
            logger.info("ℹ️ Info alert", **alert)
    
    def record_agent_request(
        self, 
        agent_id: str, 
        response_time: float, 
        success: bool = True,
        priority: str = "normal"
    ):
        """Record agent request metrics with enhanced tracking"""
        
        if agent_id not in self.agent_metrics:
            self.agent_metrics[agent_id] = AgentPerformanceMetrics(agent_id=agent_id)
        
        metrics = self.agent_metrics[agent_id]
        
        # Update basic metrics
        metrics.requests_processed += 1
        metrics.last_activity = datetime.now()
        
        if success:
            metrics.successful_requests += 1
            
            # Update response time statistics
            metrics.total_response_time += response_time
            metrics.avg_response_time = metrics.total_response_time / metrics.successful_requests
            metrics.min_response_time = min(metrics.min_response_time, response_time)
            metrics.max_response_time = max(metrics.max_response_time, response_time)
        else:
            metrics.failed_requests += 1
        
        # Update Prometheus metrics
        status = "success" if success else "error"
        self.agent_requests_total.labels(
            agent_id=agent_id,
            status=status,
            priority=priority
        ).inc()
        
        if success:
            self.agent_response_time.labels(
                agent_id=agent_id,
                agent_type=agent_id.split('_')[0] if '_' in agent_id else agent_id
            ).observe(response_time)
    
    def record_workflow_execution(
        self,
        workflow_id: str,
        workflow_type: str,
        execution_time: float,
        quality_score: float = 0.95,
        agents_involved: List[str] = None,
        success: bool = True,
        state_transitions: List[Dict[str, Any]] = None
    ):
        """Record comprehensive workflow execution metrics"""
        
        # Create or update workflow metrics
        if workflow_id not in self.workflow_metrics:
            self.workflow_metrics[workflow_id] = WorkflowMetrics(
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                start_time=datetime.now() - timedelta(seconds=execution_time)
            )
        
        workflow_metrics = self.workflow_metrics[workflow_id]
        workflow_metrics.end_time = datetime.now()
        workflow_metrics.execution_time = execution_time
        workflow_metrics.quality_score = quality_score
        workflow_metrics.agents_involved = agents_involved or []
        workflow_metrics.success = success
        workflow_metrics.state_transitions = state_transitions or []
        
        # Determine complexity
        complexity = "simple"
        if len(agents_involved or []) > 3:
            complexity = "complex"
        elif execution_time > 20:
            complexity = "complex"
        elif len(state_transitions or []) > 10:
            complexity = "complex"
        
        # Update Prometheus metrics
        self.workflow_executions_total.labels(
            workflow_type=workflow_type,
            status="success" if success else "error",
            complexity=complexity
        ).inc()
        
        self.workflow_execution_time.labels(
            workflow_type=workflow_type
        ).observe(execution_time)
        
        self.workflow_quality_score.labels(
            workflow_type=workflow_type
        ).observe(quality_score)
    
    def record_team_collaboration(
        self,
        collaboration_type: str,
        agents_involved: List[str],
        coordination_time: float,
        success: bool = True
    ):
        """Record agent team collaboration metrics"""
        
        team_size = str(len(agents_involved))
        
        # Update team collaboration metrics
        self.team_collaboration_requests.labels(
            collaboration_type=collaboration_type,
            agents_involved=str(len(agents_involved)),
            status="success" if success else "error"
        ).inc()
        
        self.team_coordination_time.labels(
            team_size=team_size
        ).observe(coordination_time)
    
    def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive monitoring data for dashboard"""
        
        return {
            "system_health": {
                "score": self.calculate_system_health(),
                "timestamp": datetime.now().isoformat()
            },
            "agent_metrics": {
                agent_id: metrics.to_dict() 
                for agent_id, metrics in self.agent_metrics.items()
            },
            "workflow_metrics": {
                "total_workflows": len(self.workflow_metrics),
                "active_workflows": len([w for w in self.workflow_metrics.values() if w.end_time is None]),
                "average_execution_time": self._calculate_avg_workflow_time(),
                "average_quality_score": self._calculate_avg_quality_score(),
                "success_rate": self._calculate_workflow_success_rate()
            },
            "recent_alerts": self.system_alerts[-10:],
            "performance_baselines": self.performance_baselines,
            "system_resource_usage": self._get_system_resource_usage(),
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_workflow_success_rate(self) -> float:
        """Calculate workflow success rate"""
        completed_workflows = [w for w in self.workflow_metrics.values() if w.end_time is not None]
        if not completed_workflows:
            return 100.0
        
        successful_workflows = [w for w in completed_workflows if w.success]
        return (len(successful_workflows) / len(completed_workflows)) * 100
    
    def _get_system_resource_usage(self) -> Dict[str, Any]:
        """Get current system resource usage"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            disk = psutil.disk_usage('/')
            
            return {
                "memory": {
                    "used_percent": memory.percent,
                    "available_gb": memory.available / (1024**3),
                    "total_gb": memory.total / (1024**3)
                },
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "disk": {
                    "used_percent": disk.percent,
                    "free_gb": disk.free / (1024**3),
                    "total_gb": disk.total / (1024**3)
                }
            }
        except Exception as e:
            logger.error("Error getting system resource usage", error=str(e))
            return {}
    
    async def shutdown(self):
        """Gracefully shutdown the monitoring system"""
        logger.info("🛑 Shutting down monitoring system")
        self.monitoring_active = False
        
        # Final performance report
        final_report = self.get_monitoring_dashboard_data()
        logger.info("Final performance report", **final_report)

# Global monitoring instance
monitoring_system = UberEatsMonitoringSystem()