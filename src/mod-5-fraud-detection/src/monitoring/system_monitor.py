"""Comprehensive monitoring and alerting system for fraud detection.

Provides real-time system health monitoring, performance metrics collection,
security event tracking, and automated alerting for production operations.
"""

import asyncio
import json
import logging
import psutil
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
import threading
from pathlib import Path

from src.utils.circuit_breaker import circuit_breaker_manager

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics tracked."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Alert:
    """System alert representation."""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "fraud_detection_system"
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Metric:
    """System metric representation."""
    name: str
    value: Union[int, float]
    type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SystemMonitor:
    """Comprehensive system monitoring and alerting."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize system monitor.
        
        Args:
            config: Monitor configuration
        """
        self.config = config or {}
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alerts: List[Alert] = []
        self.health_checks: Dict[str, HealthCheck] = {}
        
        # Alert thresholds
        self.thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "disk_usage": 90.0,
            "fraud_detection_latency_ms": 5000,
            "error_rate_percent": 5.0,
            "circuit_breaker_failures": 5
        }
        
        # Update thresholds from config
        self.thresholds.update(self.config.get("thresholds", {}))
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_thread = None
        self._lock = threading.RLock()
        
        # Performance tracking
        self.performance_stats = {
            "fraud_detection_requests": 0,
            "fraud_detection_errors": 0,
            "fraud_detection_latency_sum": 0.0,
            "security_violations": 0,
            "blocked_transactions": 0,
            "flagged_transactions": 0
        }
        
        # Security event tracking
        self.security_events = deque(maxlen=1000)
        
        logger.info("System monitor initialized with thresholds: %s", self.thresholds)
    
    def start_monitoring(self, interval: float = 30.0):
        """Start background monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self._monitoring_thread.start()
        
        logger.info(f"Started system monitoring with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
        logger.info("Stopped system monitoring")
    
    def _monitoring_loop(self, interval: float):
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                self._collect_system_metrics()
                self._collect_application_metrics()
                self._check_health()
                self._evaluate_alerts()
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)
    
    def _collect_system_metrics(self):
        """Collect system-level metrics."""
        timestamp = datetime.now()
        
        # CPU usage
        cpu_percent = psutil.cpu_percent()
        self.record_metric("system_cpu_usage", cpu_percent, MetricType.GAUGE, unit="%")
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.record_metric("system_memory_usage", memory.percent, MetricType.GAUGE, unit="%")
        self.record_metric("system_memory_available_gb", memory.available / (1024**3), MetricType.GAUGE, unit="GB")
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        self.record_metric("system_disk_usage", disk_percent, MetricType.GAUGE, unit="%")
        
        # Network I/O
        network = psutil.net_io_counters()
        self.record_metric("system_network_bytes_sent", network.bytes_sent, MetricType.COUNTER, unit="bytes")
        self.record_metric("system_network_bytes_recv", network.bytes_recv, MetricType.COUNTER, unit="bytes")
        
        # Load average (Unix-like systems)
        try:
            load1, load5, load15 = psutil.getloadavg()
            self.record_metric("system_load_1min", load1, MetricType.GAUGE)
            self.record_metric("system_load_5min", load5, MetricType.GAUGE)
            self.record_metric("system_load_15min", load15, MetricType.GAUGE)
        except AttributeError:
            # getloadavg not available on Windows
            pass
    
    def _collect_application_metrics(self):
        """Collect application-specific metrics."""
        with self._lock:
            # Fraud detection performance
            total_requests = self.performance_stats["fraud_detection_requests"]
            total_errors = self.performance_stats["fraud_detection_errors"]
            
            if total_requests > 0:
                error_rate = (total_errors / total_requests) * 100
                avg_latency = self.performance_stats["fraud_detection_latency_sum"] / total_requests
                
                self.record_metric("fraud_detection_error_rate", error_rate, MetricType.GAUGE, unit="%")
                self.record_metric("fraud_detection_avg_latency", avg_latency, MetricType.GAUGE, unit="ms")
            
            # Security metrics
            self.record_metric("security_violations_total", self.performance_stats["security_violations"], MetricType.COUNTER)
            self.record_metric("blocked_transactions_total", self.performance_stats["blocked_transactions"], MetricType.COUNTER)
            self.record_metric("flagged_transactions_total", self.performance_stats["flagged_transactions"], MetricType.COUNTER)
            
            # Circuit breaker metrics
            cb_stats = circuit_breaker_manager.get_all_stats()
            for cb_name, stats in cb_stats.items():
                self.record_metric(
                    f"circuit_breaker_{cb_name}_failures",
                    stats.failed_requests,
                    MetricType.COUNTER,
                    tags={"circuit_breaker": cb_name}
                )
                
                if stats.total_requests > 0:
                    failure_rate = (stats.failed_requests / stats.total_requests) * 100
                    self.record_metric(
                        f"circuit_breaker_{cb_name}_failure_rate",
                        failure_rate,
                        MetricType.GAUGE,
                        unit="%",
                        tags={"circuit_breaker": cb_name}
                    )
    
    def _check_health(self):
        """Perform health checks."""
        # System health
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        disk_usage = (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
        
        if cpu_usage > 95:
            status = "unhealthy"
            message = f"CPU usage critical: {cpu_usage:.1f}%"
        elif cpu_usage > 80:
            status = "degraded"
            message = f"CPU usage high: {cpu_usage:.1f}%"
        else:
            status = "healthy"
            message = f"CPU usage normal: {cpu_usage:.1f}%"
        
        self.health_checks["system_cpu"] = HealthCheck(
            name="system_cpu",
            status=status,
            message=message,
            metadata={"cpu_usage": cpu_usage}
        )
        
        # Memory health
        if memory_usage > 95:
            status = "unhealthy"
            message = f"Memory usage critical: {memory_usage:.1f}%"
        elif memory_usage > 85:
            status = "degraded" 
            message = f"Memory usage high: {memory_usage:.1f}%"
        else:
            status = "healthy"
            message = f"Memory usage normal: {memory_usage:.1f}%"
        
        self.health_checks["system_memory"] = HealthCheck(
            name="system_memory",
            status=status,
            message=message,
            metadata={"memory_usage": memory_usage}
        )
        
        # Application health
        with self._lock:
            total_requests = self.performance_stats["fraud_detection_requests"]
            total_errors = self.performance_stats["fraud_detection_errors"]
            
            if total_requests > 0:
                error_rate = (total_errors / total_requests) * 100
                
                if error_rate > 10:
                    status = "unhealthy"
                    message = f"High error rate: {error_rate:.1f}%"
                elif error_rate > 5:
                    status = "degraded"
                    message = f"Elevated error rate: {error_rate:.1f}%"
                else:
                    status = "healthy"
                    message = f"Error rate normal: {error_rate:.1f}%"
            else:
                status = "healthy"
                message = "No requests processed yet"
            
            self.health_checks["fraud_detection"] = HealthCheck(
                name="fraud_detection",
                status=status,
                message=message,
                metadata={"error_rate": error_rate if total_requests > 0 else 0}
            )
    
    def _evaluate_alerts(self):
        """Evaluate alert conditions."""
        # CPU alert
        cpu_usage = psutil.cpu_percent()
        if cpu_usage > self.thresholds["cpu_usage"]:
            self._create_alert(
                "high_cpu_usage",
                AlertSeverity.HIGH if cpu_usage > 90 else AlertSeverity.MEDIUM,
                "High CPU Usage",
                f"CPU usage is {cpu_usage:.1f}% (threshold: {self.thresholds['cpu_usage']}%)",
                {"cpu_usage": cpu_usage}
            )
        
        # Memory alert
        memory_usage = psutil.virtual_memory().percent
        if memory_usage > self.thresholds["memory_usage"]:
            self._create_alert(
                "high_memory_usage",
                AlertSeverity.HIGH if memory_usage > 95 else AlertSeverity.MEDIUM,
                "High Memory Usage",
                f"Memory usage is {memory_usage:.1f}% (threshold: {self.thresholds['memory_usage']}%)",
                {"memory_usage": memory_usage}
            )
        
        # Error rate alert
        with self._lock:
            total_requests = self.performance_stats["fraud_detection_requests"]
            total_errors = self.performance_stats["fraud_detection_errors"]
            
            if total_requests > 10:  # Only alert if we have sufficient data
                error_rate = (total_errors / total_requests) * 100
                
                if error_rate > self.thresholds["error_rate_percent"]:
                    self._create_alert(
                        "high_error_rate",
                        AlertSeverity.HIGH if error_rate > 15 else AlertSeverity.MEDIUM,
                        "High Error Rate",
                        f"Error rate is {error_rate:.1f}% (threshold: {self.thresholds['error_rate_percent']}%)",
                        {"error_rate": error_rate, "total_requests": total_requests}
                    )
        
        # Circuit breaker alerts
        cb_stats = circuit_breaker_manager.get_all_stats()
        for cb_name, stats in cb_stats.items():
            if stats.consecutive_failures >= self.thresholds["circuit_breaker_failures"]:
                self._create_alert(
                    f"circuit_breaker_{cb_name}_failures",
                    AlertSeverity.HIGH,
                    "Circuit Breaker Failures",
                    f"Circuit breaker '{cb_name}' has {stats.consecutive_failures} consecutive failures",
                    {"circuit_breaker": cb_name, "failures": stats.consecutive_failures}
                )
    
    def _create_alert(self, alert_id: str, severity: AlertSeverity, title: str, 
                     message: str, metadata: Dict[str, Any]):
        """Create or update an alert."""
        # Check if alert already exists and is unresolved
        existing_alert = next((a for a in self.alerts if a.id == alert_id and not a.resolved), None)
        
        if existing_alert:
            # Update existing alert
            existing_alert.message = message
            existing_alert.timestamp = datetime.now()
            existing_alert.metadata.update(metadata)
        else:
            # Create new alert
            alert = Alert(
                id=alert_id,
                severity=severity,
                title=title,
                message=message,
                metadata=metadata
            )
            
            self.alerts.append(alert)
            logger.warning(f"ALERT [{severity.value.upper()}] {title}: {message}")
            
            # Trigger alert handlers
            self._handle_alert(alert)
    
    def _handle_alert(self, alert: Alert):
        """Handle new alert (send notifications, etc.)."""
        # Log to file for persistence
        self._log_alert_to_file(alert)
        
        # For critical alerts, you might want to send notifications
        if alert.severity == AlertSeverity.CRITICAL:
            logger.critical(f"CRITICAL ALERT: {alert.title} - {alert.message}")
            # TODO: Integrate with notification systems (email, Slack, PagerDuty, etc.)
    
    def _log_alert_to_file(self, alert: Alert):
        """Log alert to file for persistence."""
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            alert_file = log_dir / "alerts.json"
            
            alert_data = {
                "id": alert.id,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "source": alert.source,
                "metadata": alert.metadata
            }
            
            with open(alert_file, "a") as f:
                f.write(json.dumps(alert_data) + "\n")
                
        except Exception as e:
            logger.error(f"Failed to log alert to file: {e}")
    
    def record_metric(self, name: str, value: Union[int, float], 
                     metric_type: MetricType, unit: str = "", 
                     tags: Dict[str, str] = None):
        """Record a metric value.
        
        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            unit: Unit of measurement
            tags: Additional tags
        """
        metric = Metric(
            name=name,
            value=value,
            type=metric_type,
            unit=unit,
            tags=tags or {}
        )
        
        self.metrics[name].append(metric)
    
    def record_fraud_detection_request(self, duration_ms: float, success: bool,
                                     action: str = ""):
        """Record fraud detection request metrics.
        
        Args:
            duration_ms: Request duration in milliseconds
            success: Whether request was successful
            action: Action taken (BLOCK, FLAG, ALLOW, etc.)
        """
        with self._lock:
            self.performance_stats["fraud_detection_requests"] += 1
            self.performance_stats["fraud_detection_latency_sum"] += duration_ms
            
            if not success:
                self.performance_stats["fraud_detection_errors"] += 1
            
            if action == "BLOCK":
                self.performance_stats["blocked_transactions"] += 1
            elif action in ["FLAG", "REQUIRE_HUMAN"]:
                self.performance_stats["flagged_transactions"] += 1
        
        # Check for latency alerts
        if duration_ms > self.thresholds["fraud_detection_latency_ms"]:
            self._create_alert(
                "high_fraud_detection_latency",
                AlertSeverity.MEDIUM,
                "High Fraud Detection Latency",
                f"Request took {duration_ms:.0f}ms (threshold: {self.thresholds['fraud_detection_latency_ms']}ms)",
                {"duration_ms": duration_ms}
            )
    
    def record_security_violation(self, violation_type: str, details: Dict[str, Any]):
        """Record a security violation.
        
        Args:
            violation_type: Type of violation
            details: Violation details
        """
        with self._lock:
            self.performance_stats["security_violations"] += 1
        
        security_event = {
            "timestamp": datetime.now().isoformat(),
            "type": violation_type,
            "details": details
        }
        
        self.security_events.append(security_event)
        
        # Create security alert
        self._create_alert(
            f"security_violation_{violation_type}",
            AlertSeverity.HIGH,
            "Security Violation",
            f"Security violation detected: {violation_type}",
            {"violation_type": violation_type, **details}
        )
        
        logger.warning(f"Security violation recorded: {violation_type} - {details}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status.
        
        Returns:
            System status summary
        """
        # System metrics
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Application metrics
        with self._lock:
            total_requests = self.performance_stats["fraud_detection_requests"]
            total_errors = self.performance_stats["fraud_detection_errors"]
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0.0
            avg_latency = (self.performance_stats["fraud_detection_latency_sum"] / total_requests) if total_requests > 0 else 0.0
        
        # Health status
        overall_health = "healthy"
        unhealthy_checks = [hc for hc in self.health_checks.values() if hc.status == "unhealthy"]
        degraded_checks = [hc for hc in self.health_checks.values() if hc.status == "degraded"]
        
        if unhealthy_checks:
            overall_health = "unhealthy"
        elif degraded_checks:
            overall_health = "degraded"
        
        # Active alerts
        active_alerts = [a for a in self.alerts if not a.resolved]
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_health": overall_health,
            "system": {
                "cpu_usage": cpu_usage,
                "memory_usage": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_usage": (disk.used / disk.total) * 100,
                "disk_free_gb": disk.free / (1024**3)
            },
            "fraud_detection": {
                "total_requests": total_requests,
                "error_rate": error_rate,
                "avg_latency_ms": avg_latency,
                "blocked_transactions": self.performance_stats["blocked_transactions"],
                "flagged_transactions": self.performance_stats["flagged_transactions"],
                "security_violations": self.performance_stats["security_violations"]
            },
            "health_checks": {
                name: {
                    "status": hc.status,
                    "message": hc.message,
                    "timestamp": hc.timestamp.isoformat()
                }
                for name, hc in self.health_checks.items()
            },
            "alerts": {
                "active": len(active_alerts),
                "critical": len(critical_alerts),
                "recent": [
                    {
                        "id": a.id,
                        "severity": a.severity.value,
                        "title": a.title,
                        "message": a.message,
                        "timestamp": a.timestamp.isoformat()
                    }
                    for a in sorted(active_alerts, key=lambda x: x.timestamp, reverse=True)[:5]
                ]
            },
            "circuit_breakers": {
                name: {
                    "total_requests": stats.total_requests,
                    "failed_requests": stats.failed_requests,
                    "consecutive_failures": stats.consecutive_failures
                }
                for name, stats in circuit_breaker_manager.get_all_stats().items()
            }
        }
    
    def get_metrics(self, metric_name: str = None, 
                   time_range_minutes: int = 60) -> Dict[str, List[Dict[str, Any]]]:
        """Get metrics data.
        
        Args:
            metric_name: Specific metric to retrieve (None for all)
            time_range_minutes: Time range in minutes
            
        Returns:
            Metrics data
        """
        cutoff_time = datetime.now() - timedelta(minutes=time_range_minutes)
        
        result = {}
        
        metrics_to_process = [metric_name] if metric_name else self.metrics.keys()
        
        for name in metrics_to_process:
            if name in self.metrics:
                filtered_metrics = [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "value": m.value,
                        "type": m.type.value,
                        "unit": m.unit,
                        "tags": m.tags
                    }
                    for m in self.metrics[name]
                    if m.timestamp >= cutoff_time
                ]
                
                if filtered_metrics:
                    result[name] = filtered_metrics
        
        return result
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert.
        
        Args:
            alert_id: Alert ID to resolve
        """
        alert = next((a for a in self.alerts if a.id == alert_id and not a.resolved), None)
        
        if alert:
            alert.resolved = True
            alert.resolution_time = datetime.now()
            logger.info(f"Resolved alert: {alert_id}")
        else:
            logger.warning(f"Alert not found or already resolved: {alert_id}")


# Global system monitor instance
system_monitor = SystemMonitor()


def start_monitoring(interval: float = 30.0, config: Dict[str, Any] = None):
    """Start system monitoring.
    
    Args:
        interval: Monitoring interval in seconds
        config: Monitor configuration
    """
    global system_monitor
    if config:
        system_monitor = SystemMonitor(config)
    
    system_monitor.start_monitoring(interval)


def stop_monitoring():
    """Stop system monitoring."""
    system_monitor.stop_monitoring()


def get_system_status() -> Dict[str, Any]:
    """Get current system status."""
    return system_monitor.get_system_status()


def record_fraud_detection_request(duration_ms: float, success: bool, action: str = ""):
    """Record fraud detection request metrics."""
    system_monitor.record_fraud_detection_request(duration_ms, success, action)


def record_security_violation(violation_type: str, details: Dict[str, Any]):
    """Record a security violation."""
    system_monitor.record_security_violation(violation_type, details)