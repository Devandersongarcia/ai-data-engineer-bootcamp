# Airflow 3.0 Specialist

## Expertise Areas

- Asset-aware scheduling and event-driven workflows
- TaskFlow API with new decorators
- Multi-executor configuration and optimization
- DAG versioning and performance tuning

## Asset-Driven Patterns

### Basic Asset DAG
```python
from airflow.sdk import Asset
from airflow.decorators import asset, task

@asset(uri="s3://bucket/invoices/{ds}", schedule=None)
def invoice_pipeline():
    """Main pipeline triggered by invoice file events."""
    
    @task.run_if(lambda ctx: ctx["params"].get("process", True))
    def extract():
        """Extract invoice data when processing is enabled."""
        pass
    
    @task.skip_if(lambda ctx: ctx["ti"].xcom_pull()["confidence"] < 0.7)
    def validate():
        """Validate extraction only for high-confidence results."""
        pass
    
    return extract() >> validate()
```

### Asset Event Handling
```python
def process_asset_events(**context):
    """Handle incoming asset events with metadata extraction."""
    asset_events = context.get("asset_events", {})
    
    for asset, event in asset_events.items():
        file_path = asset.uri
        metadata = event.extra or {}
        
        yield {
            "file_path": file_path,
            "event_metadata": metadata,
            "processing_timestamp": context["logical_date"]
        }
```

## Multi-Executor Strategy

### Executor Assignment
```python
@task(executor="kubernetes")
def cpu_intensive_task():
    """Model detection requiring significant CPU resources."""
    pass

@task(executor="celery") 
def standard_processing():
    """Standard data transformation tasks."""
    pass

@task(executor="sequential")
def database_operations():
    """Database operations requiring serialized execution."""
    pass
```

## Conditional Task Execution

### Skip Conditions
```python
@task.skip_if(lambda ctx: should_skip_processing(ctx))
def optional_processing():
    """Process data only when specific conditions are met."""
    pass

def should_skip_processing(context):
    """Determine if processing should be skipped based on context."""
    params = context.get("params", {})
    return not params.get("enable_processing", True)
```

### Run Conditions
```python
@task.run_if(lambda ctx: meets_quality_threshold(ctx))
def quality_dependent_task():
    """Execute only when quality metrics meet threshold."""
    pass

def meets_quality_threshold(context):
    """Check if upstream task results meet quality requirements."""
    upstream_result = context["ti"].xcom_pull(task_ids="quality_check")
    return upstream_result.get("score", 0) >= 0.8
```

## Asset Outlet Management

### Asset Creation
```python
from airflow.sdk import Asset

extracted_data_asset = Asset(
    name="invoice_data_extracted",
    uri="postgres://invoice_db/extractions/{ds}"
)

@task(outlets=[extracted_data_asset])
def store_extraction_results():
    """Store extraction results and emit asset event."""
    pass
```

### Asset Metadata
```python
@task
def emit_asset_with_metadata(**context):
    """Emit asset event with processing metadata."""
    asset = extracted_data_asset
    
    context["outlet_events"][asset].extra = {
        "record_count": 150,
        "processing_duration": 45.2,
        "confidence_score": 0.92
    }
    
    return {"status": "completed"}
```

## Performance Optimization

### Resource Management
```python
@task(
    pool="database_pool",
    pool_slots=2,
    max_active_tis_per_dag=1
)
def database_intensive_task():
    """Database operation with resource constraints."""
    pass
```

### Parallel Processing
```python
@task
def parallel_extraction():
    """Extract data from multiple sources in parallel."""
    from airflow.operators.python import get_current_context
    
    context = get_current_context()
    file_list = context["params"]["files"]
    
    return file_list

@task.expand(file_path=parallel_extraction())
def process_single_file(file_path: str):
    """Process individual file in parallel execution."""
    pass
```

## Error Recovery Patterns

### Retry Configuration
```python
@task(
    retries=3,
    retry_delay=timedelta(minutes=5),
    retry_exponential_backoff=True,
    max_retry_delay=timedelta(hours=1)
)
def resilient_api_call():
    """API call with intelligent retry strategy."""
    pass
```

### Failure Handling
```python
@task(trigger_rule="one_failed")
def handle_failures(**context):
    """Handle task failures with appropriate recovery actions."""
    failed_task_instances = context["dag_run"].get_task_instances(
        state="failed"
    )
    
    for ti in failed_task_instances:
        log_failure_details(ti.task_id, ti.log_url)
        notify_operations_team(ti.dag_id, ti.task_id)
```

## Monitoring Integration

### Custom Metrics
```python
@task
def emit_processing_metrics(**context):
    """Emit custom metrics for monitoring dashboard."""
    from airflow.providers.prometheus.hooks.prometheus import PrometheusHook
    
    hook = PrometheusHook()
    hook.send_metric("invoice_processed_total", 1, {"dag_id": context["dag"].dag_id})
```

### Health Checks
```python
@task.sensor(poke_interval=30, timeout=300)
def system_health_check():
    """Monitor system health before processing."""
    return check_database_connectivity() and check_api_availability()
```