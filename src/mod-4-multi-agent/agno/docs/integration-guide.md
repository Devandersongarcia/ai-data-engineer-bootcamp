# 🔗 Integration Guide

## Overview
This guide covers integrating the UberEats Multi-Agent System with external services, databases, and real-time streaming platforms.

## 🚀 Kafka Integration

### Setup and Configuration

#### 1. Kafka Topics Creation
```bash
# Create all required topics
python tests/create_output_topics.py

# Manual topic creation
kafka-topics.sh --create --topic gps-events --partitions 12 --replication-factor 3
kafka-topics.sh --create --topic eta-predictions --partitions 6 --replication-factor 3
kafka-topics.sh --create --topic route-optimizations --partitions 6 --replication-factor 3
kafka-topics.sh --create --topic driver-allocations --partitions 6 --replication-factor 3
```

#### 2. Producer Configuration
```python
# data/kafka_config.py
producer_config = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'ubereats-agent-producer',
    'acks': 'all',
    'retries': 3,
    'batch.size': 16384,
    'linger.ms': 10,
    'buffer.memory': 33554432
}
```

#### 3. Consumer Configuration
```python
consumer_config = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'ubereats-agents',
    'auto.offset.reset': 'latest',
    'enable.auto.commit': True,
    'session.timeout.ms': 30000,
    'max.poll.records': 500
}
```

### Real-Time GPS Processing

#### GPS Event Schema
```json
{
  "driver_id": "driver_123",
  "order_id": "order_456",
  "location": {
    "lat": -23.5505,
    "lon": -46.6333
  },
  "speed_kph": 25.3,
  "trip_stage": "to_pickup",
  "traffic_density": "moderate",
  "zone_type": "business_district",
  "timestamp": "2024-08-28T10:30:00Z",
  "anomaly_flags": []
}
```

#### Processing Pipeline
```python
# Real-time GPS event processing
async def process_gps_events():
    consumer = KafkaConsumer('gps-events', **consumer_config)
    
    for message in consumer:
        gps_event = json.loads(message.value)
        
        # Trigger appropriate agents
        active_agents = determine_active_agents(gps_event)
        
        for agent_type in active_agents:
            agent = get_agent(agent_type)
            result = await agent.process(gps_event)
            
            # Publish results
            await publish_agent_result(agent_type, result)
```

### Agent Output Publishing

#### ETA Predictions
```python
# Publishing ETA results
async def publish_eta_prediction(prediction):
    message = {
        "order_id": prediction.order_id,
        "driver_id": prediction.driver_id,
        "pickup_eta": prediction.pickup_eta,
        "delivery_eta": prediction.delivery_eta,
        "confidence": prediction.confidence,
        "factors": prediction.factors,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await kafka_producer.send('eta-predictions', json.dumps(message))
```

#### Route Optimizations
```python
# Publishing route changes
async def publish_route_optimization(route_data):
    message = {
        "driver_id": route_data.driver_id,
        "original_route": route_data.original_route,
        "optimized_route": route_data.optimized_route,
        "time_savings": route_data.time_savings,
        "reason": route_data.optimization_reason,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await kafka_producer.send('route-optimizations', json.dumps(message))
```

### Dashboard Integration

#### Real-Time Data Streaming
```python
# Streamlit dashboard Kafka consumer
import streamlit as st
from kafka import KafkaConsumer
import json

@st.cache_data
def get_kafka_consumer():
    return KafkaConsumer(
        'eta-predictions',
        'route-optimizations', 
        'driver-allocations',
        **consumer_config
    )

# Real-time metrics display
def display_realtime_metrics():
    consumer = get_kafka_consumer()
    
    for message in consumer:
        data = json.loads(message.value)
        topic = message.topic
        
        if topic == 'eta-predictions':
            update_eta_dashboard(data)
        elif topic == 'route-optimizations':
            update_route_dashboard(data)
        elif topic == 'driver-allocations':
            update_driver_dashboard(data)
```

#### Performance Improvements
Recent dashboard optimizations:
- **Buffer Management**: Increased buffer sizes for high-throughput scenarios
- **Connection Pooling**: Optimized Kafka connection reuse
- **Batch Processing**: Process events in batches for better performance
- **Memory Management**: Efficient memory usage with sliding windows

## 🤖 OpenAI Integration

### Model Configuration

#### Primary Models
```python
# src/config/settings.py
openai_config = {
    "model": "gpt-4-turbo-preview",
    "temperature": 0.3,
    "max_tokens": 2000,
    "timeout": 30
}

# Fallback models
fallback_models = [
    "gpt-4-1106-preview",
    "gpt-3.5-turbo-1106"
]
```

### Agent Enhancement with OpenAI

#### ETA Prediction Enhancement
```python
class EnhancedETAAgent(UberEatsBaseAgent):
    def __init__(self):
        super().__init__(
            model=OpenAIChat(
                id="gpt-4-turbo-preview",
                api_key=settings.openai_api_key
            ),
            tools=[DatabaseTools(), AnalyticsTools(), WeatherTools()],
            instructions="""
            You are an expert ETA prediction agent for UberEats deliveries.
            
            CAPABILITIES:
            - Analyze real-time GPS data and traffic conditions
            - Consider weather impact on delivery times  
            - Factor in restaurant preparation times
            - Account for driver behavior patterns
            
            DECISION FRAMEWORK:
            1. Assess current traffic and weather conditions
            2. Analyze historical delivery patterns for similar conditions
            3. Calculate base ETA using route data
            4. Apply adjustment factors (traffic, weather, prep time)
            5. Provide confidence score (0.0-1.0)
            
            OUTPUT FORMAT:
            Always provide structured predictions with confidence scores.
            """
        )
```

#### Route Optimization with GPT-4
```python
class IntelligentRouteAgent(UberEatsBaseAgent):
    def __init__(self):
        super().__init__(
            model=OpenAIChat(id="gpt-4-turbo-preview"),
            instructions="""
            You are an expert route optimization agent with deep knowledge of:
            - São Paulo traffic patterns and geography
            - Real-time traffic condition analysis
            - Multi-stop delivery optimization
            - Driver behavior and vehicle capabilities
            
            KEY PRINCIPLES:
            - Avoid backtracking and inefficient routing patterns
            - Prioritize main arteries during peak hours
            - Consider real-time traffic data over historical patterns
            - Account for delivery time windows and customer priorities
            
            OPTIMIZATION STRATEGY:
            1. Analyze current traffic conditions across the route network
            2. Identify bottlenecks and congestion points
            3. Calculate alternative routes with time/distance trade-offs
            4. Recommend optimal route with clear reasoning
            """
        )
```

### Advanced OpenAI Features

#### Function Calling Integration
```python
# Define tools for OpenAI function calling
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_traffic_data",
            "description": "Get real-time traffic data for a specific route",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string"},
                    "destination": {"type": "string"},
                    "route_options": {"type": "array"}
                },
                "required": ["origin", "destination"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "calculate_delivery_time",
            "description": "Calculate estimated delivery time with confidence",
            "parameters": {
                "type": "object",
                "properties": {
                    "distance_km": {"type": "number"},
                    "traffic_factor": {"type": "number"},
                    "weather_conditions": {"type": "string"},
                    "driver_performance": {"type": "number"}
                }
            }
        }
    }
]
```

#### Structured Output with Pydantic
```python
from pydantic import BaseModel, Field

class ETAPrediction(BaseModel):
    order_id: str
    pickup_eta_minutes: float = Field(gt=0, description="ETA to pickup location")
    delivery_eta_minutes: float = Field(gt=0, description="ETA to delivery location") 
    confidence_score: float = Field(ge=0, le=1, description="Prediction confidence")
    factors: list[str] = Field(description="Factors affecting the ETA")
    alternative_routes: Optional[list[dict]] = None

# Use structured output
response = openai_client.beta.chat.completions.parse(
    model="gpt-4-turbo-preview",
    messages=[{"role": "user", "content": eta_request}],
    response_format=ETAPrediction
)
```

### Error Handling and Resilience

#### Retry Logic
```python
import backoff

@backoff.on_exception(
    backoff.expo,
    openai.RateLimitError,
    max_tries=3,
    max_time=60
)
async def call_openai_with_retry(messages, **kwargs):
    return await openai_client.chat.completions.create(
        messages=messages,
        **kwargs
    )
```

#### Fallback Strategies
```python
async def robust_agent_call(agent, input_data):
    try:
        # Primary OpenAI model
        result = await agent.arun(input_data)
        return result
    except openai.RateLimitError:
        # Fallback to local model or cached response
        logger.warning("OpenAI rate limit hit, using fallback")
        return await fallback_prediction(input_data)
    except Exception as e:
        logger.error(f"Agent call failed: {e}")
        return default_response(input_data)
```

## 🗄️ Database Integration

### PostgreSQL Setup
```python
# Connection with pooling
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600
)
```

### MongoDB Integration
```python
# Async MongoDB client
from motor.motor_asyncio import AsyncIOMotorClient

mongo_client = AsyncIOMotorClient(
    settings.mongodb_connection_string,
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=30000
)
```

### Redis Configuration
```python
# Redis connection pool
import redis.asyncio as redis

redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=20,
    retry_on_timeout=True
)
```

## 📊 Monitoring Integration

### Langfuse Observability
```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_host
)

# Agent execution tracking
@langfuse.observe(as_type="generation")
async def agent_execution(agent_type: str, input_data: dict):
    result = await agent.process(input_data)
    
    # Automatic metrics collection
    langfuse.score(
        name="agent_performance",
        value=result.confidence,
        comment=f"Agent: {agent_type}"
    )
    
    return result
```

### Prometheus Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

# Agent performance metrics
AGENT_CALLS = Counter('agent_calls_total', ['agent_type', 'status'])
AGENT_DURATION = Histogram('agent_duration_seconds', ['agent_type'])
ACTIVE_SESSIONS = Gauge('active_sessions_current', ['agent_type'])

# Kafka metrics
KAFKA_MESSAGES = Counter('kafka_messages_total', ['topic', 'status'])
KAFKA_LAG = Gauge('kafka_consumer_lag', ['topic', 'partition'])
```

## 🔧 Configuration Management

### Environment Variables
```bash
# Core services
DATABASE_URL="postgresql://user:pass@localhost:5432/ubereats"
MONGODB_CONNECTION_STRING="mongodb://localhost:27017"
REDIS_URL="redis://localhost:6379"

# External APIs
OPENAI_API_KEY="sk-..."
WEATHER_API_KEY="..."
MAPS_API_KEY="..."

# Kafka
KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
KAFKA_GROUP_ID="ubereats-agents"

# Observability
LANGFUSE_PUBLIC_KEY="pk-..."
LANGFUSE_SECRET_KEY="sk-..."
PROMETHEUS_PORT="9090"
```

### Dynamic Configuration
```python
# Runtime configuration updates
class DynamicConfig:
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url)
    
    async def update_agent_config(self, agent_type: str, config: dict):
        await self.redis_client.hset(
            f"agent_config:{agent_type}",
            mapping=config
        )
    
    async def get_agent_config(self, agent_type: str):
        return await self.redis_client.hgetall(f"agent_config:{agent_type}")
```

This integration guide provides comprehensive coverage of connecting your multi-agent system with external services while maintaining performance, reliability, and observability.