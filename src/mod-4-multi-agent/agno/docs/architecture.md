# 🏗️ System Architecture

## Overview
The UberEats Multi-Agent System is built on a modern, scalable architecture using Agno 1.1+ framework with enterprise-grade capabilities.

## 📐 Core Architecture

### System Stack
```
┌─────────────────────────────────────────────┐
│             UberEats Agents                 │
│  (ETA, Driver Allocation, Route Optimization) │
├─────────────────────────────────────────────┤
│           Advanced Tools Layer              │
│  • Reasoning Tools                          │
│  • Predictive Analytics                     │
│  • Datastore Connectors                    │
├─────────────────────────────────────────────┤
│           Data Access Layer                 │
│  • PostgreSQL (Orders, Drivers, Routes)    │
│  • MongoDB (Menus, Logs, Analytics)        │
│  • Redis (Memory, Caching, Sessions)       │
├─────────────────────────────────────────────┤
│         Infrastructure Layer                │
│  • Kafka (Event Streaming)                 │
│  • FastAPI (REST/WebSocket)                │
│  • Streamlit (Dashboard)                   │
└─────────────────────────────────────────────┘
```

## 🧠 Agent Architecture

### Core Components

#### 1. Agent Framework (Agno 1.1+)
- **Base Agent Class**: Enhanced with Redis memory, observability
- **Agent Teams**: Level 4 team collaboration
- **Workflows**: Level 5 workflow orchestration with state management
- **Performance**: ~10,000x improvements over previous versions

#### 2. Tool Integration
**Database Tools**:
- PostgreSQL connector with advanced querying
- MongoDB analytics integration
- Redis memory management

**Communication Tools**:
- SMS notifications (Twilio)
- Email alerts (SendGrid)
- Slack integration

**Analytics Tools**:
- Pandas data processing
- Statistical analysis
- Predictive modeling

**External Integrations**:
- Weather APIs
- Traffic data
- Maps and routing

## 🔧 Technical Implementation

### Database Layer

#### PostgreSQL Schema
```sql
-- Core operational data
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    customer_id UUID,
    restaurant_id UUID,
    driver_id UUID,
    status VARCHAR(20),
    created_at TIMESTAMP,
    estimated_delivery TIMESTAMP
);

CREATE TABLE drivers (
    id UUID PRIMARY KEY,
    name VARCHAR(100),
    phone VARCHAR(20),
    vehicle_type VARCHAR(50),
    current_location POINT,
    status VARCHAR(20)
);

CREATE TABLE restaurants (
    id UUID PRIMARY KEY,
    name VARCHAR(100),
    address TEXT,
    location POINT,
    preparation_time_avg INTEGER
);
```

#### MongoDB Collections
```javascript
// Analytics and logs
db.delivery_analytics.createIndex({
    "delivery_date": 1,
    "driver_id": 1,
    "zone": 1
});

db.agent_logs.createIndex({
    "timestamp": 1,
    "agent_type": 1,
    "session_id": 1
});

db.performance_metrics.createIndex({
    "metric_type": 1,
    "timestamp": 1
});
```

### Kafka Architecture

#### Topic Structure
```yaml
# Real-time GPS events
gps-events:
  partitions: 12
  replication: 3
  retention: 24h

# Agent outputs
eta-predictions:
  partitions: 6
  replication: 3
  retention: 12h

route-optimizations:
  partitions: 6
  replication: 3
  retention: 12h

driver-allocations:
  partitions: 6
  replication: 3
  retention: 12h

alert-notifications:
  partitions: 3
  replication: 3
  retention: 7d
```

### Redis Configuration
```python
# Agent memory and caching
redis_config = {
    "memory": {
        "maxmemory": "2gb",
        "policy": "allkeys-lru"
    },
    "persistence": {
        "save": "900 1",  # Save if ≥1 key changed in 900s
        "aof": "everysec"
    },
    "clustering": {
        "enabled": True,
        "nodes": 3
    }
}
```

## 🚀 Advanced Features

### Model Context Protocols (MCPs)
Enterprise integration capabilities:

#### 1. Database MCP
```python
# Direct database access with security
@mcp_tool
class DatabaseMCP:
    def query_orders(self, filters: dict) -> list:
        # Secure, parameterized queries
        # Audit logging
        # Performance monitoring
```

#### 2. External Service MCP
```python
# Weather, traffic, mapping APIs
@mcp_tool
class ExternalServiceMCP:
    def get_weather_forecast(self, location: str) -> dict:
        # Cached responses
        # Fallback mechanisms
        # Rate limiting
```

### Reasoning Tools

#### Multi-Step Reasoning
```python
# Complex decision making with confidence scoring
reasoning_chain = ReasoningChain([
    AnalyzeTrafficStep(),
    PredictDelayStep(),
    OptimizeRouteStep(),
    CalculateConfidenceStep()
])
```

#### Causal Analysis
```python
# Root cause identification
causal_engine = CausalAnalysis()
root_causes = causal_engine.analyze_delivery_delay(
    delay_data=delay_metrics,
    context_factors=["weather", "traffic", "restaurant_prep"]
)
```

### Predictive Analytics

#### Demand Forecasting
```python
# ML-powered demand prediction
demand_predictor = DemandForecastingModel()
predictions = demand_predictor.forecast(
    time_horizon="4h",
    location="Vila_Olimpia",
    factors=["weather", "events", "historical"]
)
```

#### Anomaly Detection
```python
# Real-time anomaly detection
anomaly_detector = AnomalyDetector()
anomalies = anomaly_detector.detect(
    gps_events=live_gps_stream,
    thresholds=dynamic_thresholds
)
```

## 🔄 Data Flow

### Real-Time Processing Pipeline
```
GPS Device → Kafka Producer → gps-events Topic
     ↓
Kafka Consumer (Agent Orchestrator)
     ↓
Agent Activation (ETA/Route/Driver/Alert)
     ↓
Agent Processing (Tools + Reasoning)
     ↓
Results → Kafka Producer → Output Topics
     ↓
Dashboard/API Consumers
```

### Batch Processing Pipeline
```
Historical Data → MongoDB/PostgreSQL
     ↓
ETL Processing (Pandas + Spark)
     ↓
Feature Engineering
     ↓
Model Training/Inference
     ↓
Predictions → Redis Cache
     ↓
Agent Decision Support
```

## 📊 Monitoring & Observability

### Metrics Collection
```python
# Prometheus metrics
REQUEST_COUNT = Counter('requests_total', ['endpoint', 'status'])
RESPONSE_TIME = Histogram('response_duration_seconds', ['endpoint'])
AGENT_PERFORMANCE = Histogram('agent_processing_seconds', ['agent_type'])
```

### Structured Logging
```python
# Langfuse integration
logger.info(
    "agent_execution",
    agent_type="eta_prediction",
    session_id="session_123",
    processing_time=1.2,
    confidence=0.95
)
```

### Health Checks
```python
# Comprehensive health monitoring
health_checks = {
    "database": check_db_connections(),
    "kafka": check_kafka_connectivity(),
    "redis": check_redis_health(),
    "agents": check_agent_responsiveness(),
    "external_apis": check_external_services()
}
```

## 🔒 Security Architecture

### Authentication & Authorization
```python
# JWT-based authentication
auth_config = {
    "algorithm": "RS256",
    "public_key_url": "/.well-known/jwks.json",
    "issuer": "auth.ubereats.local",
    "audience": "agents-api"
}
```

### Data Protection
- Encrypted data at rest and in transit
- PII anonymization in logs
- Secure credential management
- API rate limiting and DDoS protection

### Input Validation
```python
# Comprehensive input sanitization
@validator('message')
def validate_message(cls, v):
    # XSS prevention
    # Code injection blocking
    # Size limits
    # Character validation
```

## 🌐 Scalability Considerations

### Horizontal Scaling
- Stateless agent design
- Load balancing across instances
- Database connection pooling
- Kafka partition scaling

### Performance Optimization
- Async/await throughout
- Connection pooling
- Result caching
- Query optimization

### Resource Management
```yaml
# Kubernetes resource limits
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi" 
    cpu: "1000m"
```

## 🚀 Deployment Architecture

### Container Strategy
```dockerfile
# Multi-stage production container
FROM python:3.12-slim as base
# Security hardening
# Dependency optimization
# Health check endpoints
```

### Infrastructure as Code
```yaml
# Docker Compose for development
services:
  agents:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - postgres
      - redis
      - kafka
```

This architecture provides a robust, scalable foundation for real-time delivery optimization with enterprise-grade security and monitoring capabilities.