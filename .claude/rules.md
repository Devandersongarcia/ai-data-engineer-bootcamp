# Development Rules

## Code Quality Standards

### Documentation
- Use docstrings instead of inline comments
- Docstrings must explain what, why, and how
- Keep code dry and minimal
- Apply design patterns where appropriate

### Type Safety
- Python 3.11+ with complete type hints
- Use Pydantic models for data validation
- Implement proper error handling with custom exceptions

### Design Patterns
- Factory Pattern for model detection
- Strategy Pattern for different extraction methods
- Observer Pattern for asset event handling
- Repository Pattern for database operations

## Airflow 3.0 Requirements

### Must Use Features
- Asset-aware scheduling with native watchers
- TaskFlow API with new decorators
- Multi-executor support for workload optimization

### Asset Pattern
```python
@asset(uri="s3://bucket/file", schedule=None)
def process_data():
    """Process data using asset-driven scheduling."""
    pass
```

### Conditional Tasks
```python
@task.skip_if(lambda ctx: should_skip(ctx))
def conditional_task():
    """Execute only when condition is met."""
    pass
```

## Configuration Management

### External YAML Only
- All prompts stored in YAML files
- Environment-specific configurations
- No hardcoded business logic in Python code
- Schema validation for all configs

### Configuration Structure
```yaml
models:
  vendor_a:
    detection_patterns: ["VENDOR A CORP"]
    extraction_prompt: "Extract invoice data..."
```

## LLM Integration Rules

### API Usage
- Implement retry logic with exponential backoff
- Use structured output with JSON schema validation
- Monitor token usage and costs
- Handle rate limits gracefully

### Prompt Management
- Store all prompts externally
- Version control prompt changes
- Include confidence scoring in prompts
- Implement fallback strategies

## Database Operations

### Transaction Management
- Use context managers for connections
- Implement proper rollback on failures
- Batch operations where possible
- Include audit trails for all changes

### Schema Design
- Include created_at and updated_at timestamps
- Use JSONB for flexible field storage
- Implement proper indexing strategies
- Version control all schema changes

## Error Handling

### Exception Strategy
- Create custom exception hierarchy
- Log structured error information
- Include correlation IDs for tracing
- Implement circuit breaker pattern for external APIs

### Retry Logic
- Use tenacity library for retries
- Implement exponential backoff
- Set maximum retry limits
- Log retry attempts with context

## Security Requirements

### API Keys
- Use Airflow connections for secrets
- Implement key rotation support
- Never log sensitive information
- Encrypt data at rest and in transit

### Access Control
- Principle of least privilege
- Audit all data access
- Implement proper authentication
- Use secure communication protocols

## Testing Standards

### Coverage Requirements
- Minimum 90% code coverage
- Unit tests for all business logic
- Integration tests for external APIs
- End-to-end DAG execution tests

### Test Structure
- Use pytest with fixtures
- Mock external dependencies
- Test error scenarios
- Validate configuration loading

## Performance Guidelines

### Optimization
- Use async/await for I/O operations
- Implement connection pooling
- Cache frequently accessed data
- Set appropriate resource limits

### Monitoring
- Include OpenTelemetry tracing
- Log performance metrics
- Monitor resource usage
- Set up alerting for anomalies

## Prohibited Practices

### Legacy Patterns
- No SubDAGs or deprecated operators
- Avoid BashOperator for business logic
- Do not use legacy scheduling methods
- No hardcoded file paths or configurations

### Anti-Patterns
- No god classes or functions
- Avoid deep nesting in code
- Do not ignore error handling
- No mixing of concerns in single modules