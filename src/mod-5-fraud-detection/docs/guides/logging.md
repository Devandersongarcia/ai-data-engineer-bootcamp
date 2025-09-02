# Logging Guide

Comprehensive logging system for monitoring, debugging, and tracking fraud detection operations.

## Overview

The fraud detection system includes extensive logging capabilities built on Python's logging module with correlation IDs, structured logging, and automatic log rotation.

## Logging Architecture

### Core Components

1. **`src/logging_config.py`**: Central logging configuration
2. **`src/correlation.py`**: Correlation ID management
3. **Log Files**: Organized by component and date
4. **Monitoring Integration**: Real-time log analysis

### Logging Levels

| Level | Purpose | Example Usage |
|-------|---------|---------------|
| **DEBUG** | Detailed diagnostic information | Variable values, function entry/exit |
| **INFO** | General operational information | Service startup, configuration, normal flow |
| **WARNING** | Potentially problematic situations | Deprecated features, recoverable errors |
| **ERROR** | Error conditions but app continues | API failures, connection issues |
| **CRITICAL** | Serious errors requiring attention | System failures, security violations |

## Configuration

### Environment Variables

```bash
# Logging configuration in .env
LOG_LEVEL=INFO
ENABLE_FILE_LOGGING=true
LOG_RETENTION_DAYS=30
LOG_FORMAT=structured  # or 'simple'
LOG_CORRELATION_ID=true
```

### Programmatic Configuration

```python
from src.logging_config import setup_logging
from src.correlation import get_correlation_logger

# Initialize logging system
setup_logging(log_level='INFO', enable_file_logging=True)

# Get correlation logger
logger = get_correlation_logger('fraud_detector')
```

## Log Structure

### File Organization

```
logs/
├── application/
│   ├── fraud_detection_20240101.log      # Main application logs
│   ├── streaming_20240101.log            # Streaming component logs
│   ├── agents_20240101.log               # AI agent logs
│   └── security_20240101.log             # Security-related logs
├── performance/
│   ├── metrics_20240101.log              # Performance metrics
│   ├── circuit_breaker_20240101.log      # Circuit breaker events
│   └── database_20240101.log             # Database operations
├── errors/
│   ├── errors_20240101.log               # Error aggregation
│   └── security_violations_20240101.log  # Security incidents
└── archive/
    └── older_logs/                       # Archived log files
```

### Log Entry Format

#### Structured Logging (JSON)
```json
{
  "timestamp": "2024-01-01T10:30:45.123Z",
  "level": "INFO",
  "component": "fraud_detector",
  "correlation_id": "req-123e4567-e89b-12d3-a456-426614174000",
  "message": "Processing order for fraud analysis",
  "context": {
    "order_id": "ord_789",
    "customer_id": "cust_456",
    "amount": 25.99,
    "merchant": "Restaurant ABC"
  },
  "performance": {
    "execution_time_ms": 234,
    "memory_usage_mb": 125.6
  }
}
```

#### Simple Logging (Human-readable)
```
2024-01-01 10:30:45,123 [INFO] fraud_detector [req-123e4567] Processing order for fraud analysis | order_id=ord_789 customer_id=cust_456 amount=25.99
```

## Component-Specific Logging

### Streaming Components

```python
from src.correlation import get_correlation_logger

class StreamingProcessor:
    def __init__(self):
        self.logger = get_correlation_logger('streaming_processor')
    
    def process_order(self, order):
        correlation_id = f"order-{order['id']}"
        
        with self.logger.correlation_context(correlation_id):
            self.logger.info("Starting order processing", extra={
                "order_id": order['id'],
                "order_amount": order['amount'],
                "merchant": order['merchant_name']
            })
            
            try:
                result = self._analyze_order(order)
                self.logger.info("Order processing completed", extra={
                    "fraud_score": result.fraud_score,
                    "decision": result.decision,
                    "processing_time_ms": result.processing_time
                })
                return result
            except Exception as e:
                self.logger.error("Order processing failed", extra={
                    "error": str(e),
                    "error_type": type(e).__name__
                }, exc_info=True)
                raise
```

### AI Agent Logging

```python
from src.correlation import get_correlation_logger

class AgentProcessor:
    def __init__(self):
        self.logger = get_correlation_logger('agent_processor')
    
    def analyze_with_agent(self, order_data):
        self.logger.info("Starting agent analysis", extra={
            "agent_type": "fraud_analyst",
            "input_size": len(str(order_data))
        })
        
        start_time = time.time()
        
        try:
            response = self.crew.kickoff({"order": order_data})
            
            execution_time = (time.time() - start_time) * 1000
            self.logger.info("Agent analysis completed", extra={
                "execution_time_ms": execution_time,
                "response_length": len(response),
                "agent_decision": response.get('decision', 'unknown')
            })
            
            return response
        except Exception as e:
            self.logger.error("Agent analysis failed", extra={
                "execution_time_ms": (time.time() - start_time) * 1000,
                "error": str(e)
            }, exc_info=True)
            raise
```

### Security Logging

```python
from src.correlation import get_correlation_logger

class SecurityMonitor:
    def __init__(self):
        self.logger = get_correlation_logger('security_monitor')
    
    def log_security_violation(self, violation_type, details):
        self.logger.critical("Security violation detected", extra={
            "violation_type": violation_type,
            "severity": "HIGH",
            "details": details,
            "client_ip": details.get('client_ip'),
            "user_agent": details.get('user_agent'),
            "timestamp": time.time()
        })
    
    def log_authentication_attempt(self, username, success, ip_address):
        level = "INFO" if success else "WARNING"
        self.logger.log(getattr(logging, level), "Authentication attempt", extra={
            "username": username,
            "success": success,
            "client_ip": ip_address,
            "auth_method": "api_key"
        })
```

### Database Operations Logging

```python
from src.correlation import get_correlation_logger

class DatabaseLogger:
    def __init__(self):
        self.logger = get_correlation_logger('database')
    
    def log_query(self, query, params, execution_time, rows_affected=None):
        self.logger.debug("Database query executed", extra={
            "query": query[:100] + "..." if len(query) > 100 else query,
            "execution_time_ms": execution_time * 1000,
            "rows_affected": rows_affected,
            "params_count": len(params) if params else 0
        })
    
    def log_connection_event(self, event_type, database_name):
        self.logger.info(f"Database {event_type}", extra={
            "event_type": event_type,
            "database": database_name
        })
```

## Performance Logging

### Metrics Collection

```python
from src.correlation import get_correlation_logger
from src.utils.metrics import performance_timer, memory_usage

class PerformanceLogger:
    def __init__(self):
        self.logger = get_correlation_logger('performance')
    
    @performance_timer
    def process_with_timing(self, data):
        with memory_usage() as mem:
            result = self._process_data(data)
            
        self.logger.info("Performance metrics", extra={
            "operation": "process_data",
            "execution_time_ms": mem.execution_time,
            "memory_before_mb": mem.memory_before,
            "memory_after_mb": mem.memory_after,
            "memory_delta_mb": mem.memory_delta,
            "data_size": len(str(data))
        })
        
        return result
```

### Circuit Breaker Logging

```python
from src.correlation import get_correlation_logger

class CircuitBreakerLogger:
    def __init__(self, circuit_breaker_name):
        self.logger = get_correlation_logger('circuit_breaker')
        self.cb_name = circuit_breaker_name
    
    def log_state_change(self, old_state, new_state, failure_count):
        self.logger.warning("Circuit breaker state changed", extra={
            "circuit_breaker": self.cb_name,
            "old_state": old_state,
            "new_state": new_state,
            "failure_count": failure_count,
            "severity": "HIGH" if new_state == "OPEN" else "MEDIUM"
        })
    
    def log_operation_result(self, success, execution_time):
        level = "DEBUG" if success else "WARNING"
        self.logger.log(getattr(logging, level), "Circuit breaker operation", extra={
            "circuit_breaker": self.cb_name,
            "success": success,
            "execution_time_ms": execution_time
        })
```

## Log Analysis and Monitoring

### Real-time Log Monitoring

```bash
# Monitor application logs
tail -f logs/application/fraud_detection_$(date +%Y%m%d).log

# Monitor errors specifically
tail -f logs/errors/errors_$(date +%Y%m%d).log | grep "ERROR\|CRITICAL"

# Monitor performance issues
tail -f logs/performance/metrics_$(date +%Y%m%d).log | grep "execution_time_ms.*[5-9][0-9][0-9][0-9]"
```

### Log Analysis Scripts

```python
# scripts/analyze_logs.py
import json
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_performance_logs(log_file):
    """Analyze performance metrics from structured logs"""
    metrics = defaultdict(list)
    
    with open(log_file) as f:
        for line in f:
            try:
                log_entry = json.loads(line)
                if 'performance' in log_entry:
                    component = log_entry['component']
                    exec_time = log_entry['performance']['execution_time_ms']
                    metrics[component].append(exec_time)
            except json.JSONDecodeError:
                continue
    
    # Calculate statistics
    for component, times in metrics.items():
        avg_time = sum(times) / len(times)
        max_time = max(times)
        p95_time = sorted(times)[int(0.95 * len(times))]
        
        print(f"{component}:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Maximum: {max_time:.2f}ms")
        print(f"  95th percentile: {p95_time:.2f}ms")
```

### Automated Alerting

```python
# scripts/log_alerting.py
import json
import smtplib
from datetime import datetime

class LogAlerting:
    def __init__(self):
        self.alert_thresholds = {
            'error_rate': 10,           # errors per minute
            'response_time': 5000,      # milliseconds
            'circuit_breaker_trips': 1,  # trips per hour
            'security_violations': 1     # violations per hour
        }
    
    def check_error_rate(self, log_entries):
        """Check if error rate exceeds threshold"""
        errors = [e for e in log_entries if e.get('level') in ['ERROR', 'CRITICAL']]
        error_rate = len(errors) / len(log_entries) * 60  # per minute
        
        if error_rate > self.alert_thresholds['error_rate']:
            self.send_alert(f"High error rate: {error_rate:.1f}/min")
    
    def check_performance(self, log_entries):
        """Check for performance degradation"""
        perf_entries = [e for e in log_entries if 'performance' in e]
        
        if perf_entries:
            avg_time = sum(e['performance']['execution_time_ms'] 
                          for e in perf_entries) / len(perf_entries)
            
            if avg_time > self.alert_thresholds['response_time']:
                self.send_alert(f"Performance degradation: {avg_time:.1f}ms avg")
```

## Best Practices

### 1. Correlation IDs
Always use correlation IDs to trace requests across components:

```python
# Generate correlation ID at entry point
correlation_id = f"req-{uuid.uuid4()}"

# Pass through all components
with logger.correlation_context(correlation_id):
    # All logs in this context will include the correlation ID
    process_order(order_data)
```

### 2. Structured Data
Include relevant context in log messages:

```python
logger.info("Order processed", extra={
    "order_id": order.id,
    "customer_id": order.customer_id,
    "fraud_score": result.score,
    "processing_time_ms": timer.elapsed()
})
```

### 3. Error Context
Provide sufficient context for debugging:

```python
try:
    result = process_payment(order)
except PaymentError as e:
    logger.error("Payment processing failed", extra={
        "order_id": order.id,
        "payment_method": order.payment_method,
        "amount": order.total_amount,
        "error_code": e.code,
        "error_message": str(e),
        "merchant_id": order.merchant_id
    }, exc_info=True)
```

### 4. Performance Logging
Track key performance metrics:

```python
start_time = time.time()
try:
    result = expensive_operation(data)
    logger.info("Operation completed", extra={
        "execution_time_ms": (time.time() - start_time) * 1000,
        "data_size": len(data),
        "result_size": len(result)
    })
except Exception as e:
    logger.error("Operation failed", extra={
        "execution_time_ms": (time.time() - start_time) * 1000,
        "error": str(e)
    })
```

### 5. Security Logging
Log security-relevant events:

```python
# Successful authentication
logger.info("Authentication successful", extra={
    "username": username,
    "client_ip": request.remote_addr,
    "user_agent": request.headers.get('User-Agent')
})

# Failed authentication
logger.warning("Authentication failed", extra={
    "username": username,
    "client_ip": request.remote_addr,
    "failure_reason": "invalid_credentials",
    "attempt_count": failed_attempts
})

# Security violations
logger.critical("Security violation detected", extra={
    "violation_type": "sql_injection_attempt",
    "client_ip": request.remote_addr,
    "request_data": sanitize_for_logging(request.data)
})
```

## Log Retention and Archival

### Automatic Rotation

```python
# Configure in logging_config.py
LOGGING_CONFIG = {
    'handlers': {
        'file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/application/fraud_detection.log',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,  # Keep 30 days
            'formatter': 'structured'
        }
    }
}
```

### Archival Script

```bash
#!/bin/bash
# scripts/archive_logs.sh

LOG_DIR="logs"
ARCHIVE_DIR="logs/archive"
RETENTION_DAYS=30

# Create archive directory
mkdir -p "$ARCHIVE_DIR"

# Archive logs older than retention period
find "$LOG_DIR" -name "*.log" -type f -mtime +$RETENTION_DAYS -not -path "*/archive/*" | while read -r logfile; do
    echo "Archiving $logfile"
    gzip "$logfile"
    mv "$logfile.gz" "$ARCHIVE_DIR/"
done

# Clean up very old archives (90 days)
find "$ARCHIVE_DIR" -name "*.log.gz" -type f -mtime +90 -delete
```

## Troubleshooting

### Common Logging Issues

1. **Log Files Not Created**
   - Check file permissions
   - Verify LOG_DIR environment variable
   - Ensure disk space availability

2. **Performance Impact**
   - Use appropriate log levels (avoid DEBUG in production)
   - Consider asynchronous logging for high-throughput scenarios
   - Monitor disk I/O usage

3. **Log Rotation Issues**
   - Check file permissions for log rotation
   - Verify logrotate configuration
   - Monitor disk space usage

### Diagnostic Commands

```bash
# Check log file permissions
ls -la logs/

# Monitor log file growth
watch -n 5 'du -sh logs/*'

# Check logging configuration
python -c "from src.logging_config import get_logging_config; import json; print(json.dumps(get_logging_config(), indent=2))"

# Test correlation logging
python -c "from src.correlation import get_correlation_logger; logger = get_correlation_logger('test'); logger.info('Test message')"
```

## Integration with Monitoring Systems

### ELK Stack Integration

```python
# Configure for Elasticsearch ingestion
ELASTICSEARCH_CONFIG = {
    'host': 'localhost:9200',
    'index': 'fraud-detection-logs',
    'doc_type': '_doc'
}

# Use structured logging for better parsing
logger.info("Order processed", extra={
    "@timestamp": datetime.utcnow().isoformat(),
    "service": "fraud-detection",
    "environment": "production",
    "order_id": order.id,
    "fraud_score": score
})
```

### Prometheus Metrics

```python
# Export log-based metrics
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('fraud_detection_requests_total', 'Total requests', ['status'])
REQUEST_DURATION = Histogram('fraud_detection_request_duration_seconds', 'Request duration')

def log_with_metrics(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            REQUEST_COUNT.labels(status='success').inc()
            logger.info("Request completed successfully")
            return result
        except Exception as e:
            REQUEST_COUNT.labels(status='error').inc()
            logger.error("Request failed", exc_info=True)
            raise
        finally:
            REQUEST_DURATION.observe(time.time() - start_time)
    return wrapper
```

This comprehensive logging system provides complete visibility into system operations, enabling effective monitoring, debugging, and performance optimization.