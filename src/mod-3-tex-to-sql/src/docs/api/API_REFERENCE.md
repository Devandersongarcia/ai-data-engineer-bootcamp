# API Reference - UberEats Brasil Platform

**Complete API documentation for all three environments: Development, Production, and MindsDB.**

## 🎯 Overview

This document provides comprehensive API reference for the UberEats Brasil text-to-SQL platform, covering:
- **Development Environment**: LangChain + Langfuse APIs
- **Production Environment**: Vanna.ai converter APIs  
- **MindsDB Environment**: Multi-agent system APIs

## 🧪 Development Environment APIs

### Core Text-to-SQL Converter

#### `TextToSQLConverter` Class
**Location**: `src/development/core/text_to_sql.py`

```python
from core.text_to_sql import TextToSQLConverter

# Initialize converter
converter = TextToSQLConverter()

# Process query
result = converter.process_question(
    question="Top 5 restaurantes por faturamento",
    execute_sql=True
)
```

**Methods:**

##### `process_question(question, execute_sql=True)`
Converts natural language to SQL and optionally executes it.

**Parameters:**
- `question` (str): Natural language query in Portuguese or English
- `execute_sql` (bool): Whether to execute the generated SQL

**Returns:**
```python
{
    "sql_query": "SELECT ...",
    "result": [...],  # Query results if execute_sql=True
    "metadata": {
        "execution_time": 1.23,
        "row_count": 42,
        "tokens_used": 150,
        "cost_estimate": 0.001
    }
}
```

##### `generate_sql(question)`
Generates SQL without executing it.

**Parameters:**
- `question` (str): Natural language query

**Returns:**
```python
{
    "sql_query": "SELECT ...",
    "confidence": 0.95,
    "reasoning": "Query analysis explanation"
}
```

### Langfuse Integration

#### `LangfuseService` Class
**Location**: `src/development/core/langfuse_service.py`

```python
from core.langfuse_service import LangfuseService

# Initialize service
langfuse = LangfuseService()

# Create trace
trace = langfuse.create_trace(
    name="text_to_sql_conversion",
    user_id="user_123"
)

# Add span
span = langfuse.create_span(
    trace_id=trace.id,
    name="sql_generation",
    input={"question": "..."},
    output={"sql": "..."}
)
```

**Methods:**

##### `create_trace(name, user_id=None, metadata=None)`
Creates a new trace for request tracking.

##### `create_span(trace_id, name, input=None, output=None)`
Adds a span to an existing trace.

##### `update_span(span_id, output=None, metadata=None)`
Updates an existing span with results.

## 🚀 Production Environment APIs

### Enhanced Vanna Converter

#### `VannaTextToSQLConverter` Class
**Location**: `src/production/core/vanna_converter.py`

```python
from core.vanna_converter import VannaTextToSQLConverter

# Initialize converter
converter = VannaTextToSQLConverter()

# Process query
result = converter.process_question("me mostre as notas")
```

**Methods:**

##### `process_question(question)`
High-level query processing with caching and validation.

**Parameters:**
- `question` (str): Natural language query

**Returns:**
```python
{
    "sql_query": "SELECT ...",
    "result": [...],
    "success": True,
    "execution_time": 0.15,
    "from_cache": False,
    "metadata": {
        "row_count": 41,
        "columns": ["id", "status", "total_amount"]
    }
}
```

##### `convert_to_sql(question)`
Converts query to SQL using Vanna.ai.

##### `execute_sql(sql_query)`
Executes SQL with validation and safety checks.

##### `train_model(question, sql)`
Trains Vanna.ai model with question-SQL pairs.

### Enhanced Vanna Converter (Advanced)

#### `EnhancedVannaTextToSQLConverter` Class
**Location**: `src/production/core/enhanced_vanna_converter.py`

```python
from core.enhanced_vanna_converter import EnhancedVannaTextToSQLConverter

# Initialize with specific table
converter = EnhancedVannaTextToSQLConverter(
    primary_table="payments"
)

# Switch tables at runtime
switch_result = converter.switch_table("invoices", retrain=True)
```

**Advanced Methods:**

##### `switch_table(table_name, retrain=False)`
Switches primary table context.

**Parameters:**
- `table_name` (str): Target table name
- `retrain` (bool): Whether to retrain model for new table

##### `get_table_info()`
Returns current table configuration and metadata.

##### `validate_and_execute(sql_query)`
Enhanced SQL validation and execution with safety checks.

### Connection Pool Manager

#### `ConnectionManager` Class
**Location**: `src/production/utils/connection_pool.py`

```python
from utils.connection_pool import get_connection_manager

# Get manager instance
manager = get_connection_manager()

# Execute with pooled connection
result = manager.execute_query("SELECT COUNT(*) FROM orders")

# Get pool status
status = manager.get_pool_status()
```

**Methods:**

##### `execute_query(sql_query, params=None)`
Executes query using connection pool.

##### `get_pool_status()`
Returns current pool statistics and health.

##### `reset_pool()`
Resets all connections in the pool.

## 🧠 MindsDB Environment APIs

### MindsDB Client

#### `MindsDBClient` Class
**Location**: `src/mindsdb/core/mindsdb_client.py`

```python
from core.mindsdb_client import connect

# Connect to MindsDB
server = connect("http://127.0.0.1:47334")

# Get agent
agent = server.agents.get("agent_ubereats_coordinator")

# Query agent
response = agent.completion([{
    "role": "user",
    "content": "Análise fiscal por cidade"
}])
```

**Methods:**

##### `connect(server_url)`
Creates connection to MindsDB server.

##### `agents.get(agent_name)`
Retrieves specific agent by name.

##### `agent.completion(messages)`
Sends query to agent and gets response.

### Multi-Agent Coordinator

#### `MultiAgentCoordinator` Class
**Location**: `src/mindsdb/utils/multi_agent_coordinator.py`

```python
from utils.multi_agent_coordinator import MultiAgentCoordinator

# Initialize coordinator
coordinator = MultiAgentCoordinator()

# Route query to appropriate agent
result = coordinator.route_query(
    "Total de impostos por cidade",
    preferred_agent="agent_postgres_transactions"
)
```

**Methods:**

##### `route_query(question, preferred_agent=None)`
Routes query to most appropriate agent.

##### `orchestrate_multi_agent(question)`
Coordinates multiple agents for complex queries.

##### `get_agent_capabilities()`
Returns capabilities of each available agent.

## 🔧 Configuration APIs

### Settings Management

#### Development Settings
```python
from config.settings import get_dev_settings

settings = get_dev_settings()
print(settings.openai_api_key)
print(settings.database_url)
print(settings.langfuse_enabled)
```

#### Production Settings
```python
from config.settings import get_settings

settings = get_settings()
print(settings.db_pool_size)
print(settings.query_cache_size)
print(settings.enable_performance_tracking)
```

#### MindsDB Settings
```python
from config.settings import get_settings

settings = get_settings()
print(settings.mindsdb_server_url)
print(settings.agent_name)
print(settings.openai_api_key)
```

### Table Configuration (Production)

#### `TableConfigManager` Class
**Location**: `src/production/config/table_configs.py`

```python
from config.table_configs import get_table_config_manager

# Get manager
manager = get_table_config_manager()

# Get available tables
tables = manager.get_available_tables()

# Get specific configuration
config = manager.get_config("payments")
print(config.portuguese_mappings)
print(config.training_examples)
```

## 🛠️ Utility APIs

### Logging Utilities

#### All Environments
```python
from utils.logging_utils import get_logger

# Get logger for specific module
logger = get_logger(__name__)

# Log with different levels
logger.info("Processing query")
logger.warning("Performance issue detected")
logger.error("Query execution failed")
```

### Performance Monitoring

#### Production Environment
```python
from utils.performance_utils import PerformanceTracker

# Track query performance
tracker = PerformanceTracker()

with tracker.track("sql_generation"):
    # Your code here
    result = converter.process_question(question)

# Get metrics
metrics = tracker.get_metrics()
```

#### MindsDB Environment
```python
from utils.metrics import ChatMetrics
from utils.token_manager import create_token_manager

# Track metrics
metrics = ChatMetrics()
token_manager = create_token_manager("gpt-4o-mini")

# Count tokens
token_count = token_manager.count_message_tokens(messages)

# Track performance
performance_data = metrics.get_stats()
```

## 🔍 Error Handling

### Common Error Patterns

#### Database Connection Errors
```python
from sqlalchemy.exc import OperationalError

try:
    result = converter.process_question(question)
except OperationalError as e:
    logger.error(f"Database connection failed: {e}")
    # Implement retry logic or fallback
```

#### OpenAI API Errors
```python
from openai import OpenAIError

try:
    sql_query = converter.convert_to_sql(question)
except OpenAIError as e:
    logger.error(f"OpenAI API error: {e}")
    # Implement fallback or cached response
```

#### Agent Not Found (MindsDB)
```python
from core.mindsdb_client import AgentNotFoundError

try:
    agent = server.agents.get("nonexistent_agent")
except AgentNotFoundError as e:
    logger.warning(f"Agent not found: {e}")
    # Fall back to default agent
```

## 📊 Response Formats

### Standard Response Format (All Environments)
```python
{
    "success": True,
    "data": {
        "sql_query": "SELECT ...",
        "result": [...],
        "metadata": {
            "execution_time": 1.23,
            "row_count": 42,
            "source": "production_vanna"
        }
    },
    "error": None,
    "timestamp": "2025-08-28T10:30:00Z"
}
```

### Error Response Format
```python
{
    "success": False,
    "data": None,
    "error": {
        "code": "SQL_GENERATION_FAILED",
        "message": "Unable to generate SQL for the given question",
        "details": "OpenAI API timeout"
    },
    "timestamp": "2025-08-28T10:30:00Z"
}
```

## 🚦 Rate Limiting and Quotas

### OpenAI API Limits
- **Requests per minute**: 3,500 (varies by tier)
- **Tokens per minute**: 90,000 (varies by tier)
- **Requests per day**: 200,000 (varies by tier)

### Database Connection Limits
- **Production**: 10 concurrent connections (configurable)
- **Development**: 5 concurrent connections
- **MindsDB**: Depends on database configuration

### Caching Behavior
- **Production**: 30 minutes TTL, 500 entries max
- **Development**: Basic caching, 100 entries max
- **MindsDB**: Agent-level caching, varies by configuration

## 🔐 Authentication and Security

### API Key Management
```python
# Environment variable approach (recommended)
import os
openai_key = os.getenv("OPENAI_API_KEY")

# Settings class approach
from config.settings import get_settings
settings = get_settings()
openai_key = settings.openai_api_key
```

### SQL Injection Prevention
```python
# All environments implement SQL validation
def validate_sql(sql_query):
    # Check for dangerous operations
    forbidden_keywords = ["DELETE", "DROP", "UPDATE", "INSERT"]
    
    # Validate query structure
    if any(keyword in sql_query.upper() for keyword in forbidden_keywords):
        raise ValueError("Only SELECT queries are allowed")
    
    return True
```

## 📚 Code Examples

### Development Environment Example
```python
from core.text_to_sql import TextToSQLConverter
from core.langfuse_service import LangfuseService

# Initialize components
converter = TextToSQLConverter()
langfuse = LangfuseService()

# Create trace
trace = langfuse.create_trace("query_processing")

# Process query with tracing
result = converter.process_question(
    "Top 5 restaurantes por faturamento",
    execute_sql=True
)

# Update trace
langfuse.update_trace(trace.id, output=result)
```

### Production Environment Example
```python
from core.enhanced_vanna_converter import EnhancedVannaTextToSQLConverter
from utils.connection_pool import get_connection_manager

# Initialize with connection pooling
converter = EnhancedVannaTextToSQLConverter()
manager = get_connection_manager()

# Process query with enhanced features
result = converter.process_question("me mostre as notas")

# Check pool status
status = manager.get_pool_status()
print(f"Active connections: {status['active']}")
```

### MindsDB Environment Example
```python
from core.mindsdb_client import connect
from utils.metrics import ChatMetrics

# Connect to MindsDB
server = connect("http://127.0.0.1:47334")
metrics = ChatMetrics()

# Get coordinator agent
agent = server.agents.get("agent_ubereats_coordinator")

# Process complex query
response = agent.completion([{
    "role": "user", 
    "content": "Análise completa de compliance fiscal"
}])

# Track metrics
metrics.record_query_completion(response)
```

## 🔄 Migration Between Environments

### From Development to Production
```python
# Development code
from core.text_to_sql import TextToSQLConverter
dev_converter = TextToSQLConverter()

# Production equivalent  
from core.vanna_converter import VannaTextToSQLConverter
prod_converter = VannaTextToSQLConverter()

# Same API, enhanced performance
result = prod_converter.process_question(question)
```

### From Production to MindsDB
```python
# Production code
from core.vanna_converter import VannaTextToSQLConverter
prod_converter = VannaTextToSQLConverter()

# MindsDB equivalent
from core.mindsdb_client import connect
server = connect()
agent = server.agents.get("agent_ubereats_coordinator")

# Enhanced multi-agent capabilities
response = agent.completion([{"role": "user", "content": question}])
```

---

## 📞 API Support

### Getting Help
- **Documentation**: Complete guides in `/docs` folder
- **Code Examples**: Check `/examples` directory (if available)
- **Error Handling**: Review error handling patterns above
- **Performance**: Use built-in monitoring and metrics

### Best Practices
1. **Always validate SQL** before execution
2. **Use connection pooling** in production
3. **Implement proper error handling** for all API calls
4. **Monitor token usage** to control costs
5. **Cache frequently used queries** when possible

---

**🚀 UberEats Brasil Platform APIs** - Comprehensive reference for all three environments with consistent interfaces and enhanced capabilities.