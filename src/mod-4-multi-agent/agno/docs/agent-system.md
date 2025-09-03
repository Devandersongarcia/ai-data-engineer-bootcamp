# 🤖 Agent System Guide

## Overview
The UberEats Multi-Agent System consists of specialized agents that work together to optimize delivery operations in real-time.

## 🎯 Quick Start

### 3-Step Demo
```bash
# 1. Create output topics
python tests/create_output_topics.py

# 2. Start monitoring dashboard  
python monitor_agents.py

# 3. Run agent demonstration
python demo_agent_actions.py
```

## 🧠 Agent Types

### ⏱️ ETA Prediction Agent
**Purpose**: Calculates dynamic delivery times based on real-time conditions

**Triggers**:
- Moving drivers with active orders (`trip_stage: to_pickup|to_destination`)
- Speed > 10 kph
- Valid order ID present

**Actions**:
- Calculates pickup/delivery ETAs
- Considers traffic, weather, driver behavior
- Publishes to `eta-predictions` topic

**Example**: *"ETA AGENT: Predicted 18.5min delivery for order abc123 in Vila_Olimpia with heavy traffic"*

### 🗺️ Route Optimization Agent  
**Purpose**: Finds optimal delivery routes and handles traffic conditions

**Triggers**:
- Heavy/severe traffic conditions
- High-speed highway driving (> 90 kph)
- Route optimization requests

**Actions**:
- Reroutes around traffic congestion
- Optimizes for delivery efficiency
- Avoids backtracking patterns

**Example**: *"ROUTE AGENT: Suggesting alternate route via Marginal Pinheiros to avoid heavy traffic"*

### 🎯 Driver Allocation Agent
**Purpose**: Assigns optimal drivers to new orders

**Triggers**:
- Idle drivers in business districts
- Idle drivers in city centers
- New order placement

**Actions**:
- Matches drivers to orders based on location
- Considers driver availability and performance
- Optimizes for delivery time and efficiency

**Example**: *"DRIVER AGENT: Allocating driver_456 in Itaim_Bibi to new order - optimal positioning"*

### 🚨 Alert Management Agent
**Purpose**: Detects and responds to anomalies

**Triggers**:
- GPS spoofing detection
- Speed anomalies
- Location jump detection

**Actions**:
- Flags suspicious activities
- Triggers security protocols
- Maintains system integrity

## 📊 Agent Trigger Matrix

| Scenario | ⏱️ ETA | 🗺️ Route | 🎯 Driver | 🚨 Alert | Condition |
|----------|--------|-----------|-----------|----------|-----------|
| Driver to Pickup | ✅ | - | - | - | `trip_stage: to_pickup` + `speed > 10` |
| Driver Delivering | ✅ | - | - | - | `trip_stage: to_destination` + `speed > 10` |
| Heavy Traffic | - | ✅ | - | - | `traffic_density: heavy/severe` |
| Highway Speed | - | ✅ | - | - | `speed_kph > 90` |
| Idle in Business | - | - | ✅ | - | `trip_stage: idle` + `zone_type: business_district` |
| GPS Spoofing | - | - | - | ✅ | `anomaly_flag: GPS_SPOOFING` |

## 🔄 Agent Workflows

### Multi-Agent Coordination
The system supports complex scenarios where multiple agents work together:

**Heavy Traffic + Business District**:
```json
{
  "trip_stage": "idle",
  "traffic_density": "heavy", 
  "zone_type": "business_district"
}
```
**Result**: Route Agent (rerouting) + Driver Agent (allocation)

**Active Delivery in Heavy Traffic**:
```json
{
  "trip_stage": "to_destination",
  "traffic_density": "heavy",
  "speed_kph": 15,
  "order_id": "order_789"
}
```
**Result**: ETA Agent (recalculation) + Route Agent (optimization)

## 🛠️ Advanced Features

### Agent Memory
- Redis-based persistent memory
- Session tracking across requests
- Learning from past interactions

### Performance Monitoring
- Real-time metrics via Prometheus
- Agent response times and accuracy
- System health monitoring

### Scenario Generator
Use the agent scenario generator to create custom test scenarios:
```python
# Generate test scenarios for agent validation
python scripts/generate_scenarios.py --agent eta --count 10
```

## 🚀 Integration Points

### Kafka Integration
- Real-time GPS event processing
- Agent coordination via message queues
- Scalable event-driven architecture

### Database Integration
- PostgreSQL for operational data
- MongoDB for analytics and logs
- Redis for agent memory and caching

### API Integration
- REST endpoints for external systems
- WebSocket support for real-time updates
- Authentication and rate limiting

## 🔧 Configuration

### Agent Settings
```python
# src/config/settings.py
max_concurrent_agents: int = 50
agent_timeout: int = 300
memory_limit_mb: int = 1024
```

### Trigger Sensitivity
```python
# Adjust agent trigger thresholds
ETA_MIN_SPEED = 10  # kph
TRAFFIC_HEAVY_THRESHOLD = 0.7
DRIVER_IDLE_TIMEOUT = 300  # seconds
```

## 📈 Performance Optimization

### Best Practices
1. **Parallel Processing**: Enable concurrent agent execution
2. **Memory Management**: Use Redis for state persistence
3. **Caching**: Implement result caching for frequent queries
4. **Monitoring**: Track agent performance metrics

### Scaling Guidelines
- Horizontal scaling via Kubernetes
- Load balancing for high-traffic scenarios
- Database connection pooling
- Async processing for heavy workloads