# 👤 User Guide

## Getting Started

The UberEats Multi-Agent System provides intelligent delivery optimization through specialized AI agents. This guide covers everything you need to know to use the system effectively.

## 🚀 Quick Start

### Option 1: Quick Demo (5 minutes)
```bash
# Run the quick demonstration
./quick_demo.sh

# What you'll see:
# - Agents responding to GPS events
# - Real-time ETA calculations  
# - Route optimizations
# - Driver allocations
```

### Option 2: Dashboard Interface
```bash
# Launch the interactive dashboard
./run_dashboard.sh

# Access at: http://localhost:8501
```

### Option 3: Full System Demo
```bash
# Start all components
python start_kafka_processing.py

# In another terminal:
python src/main.py
```

## 🖥️ Dashboard Interface

### Main Dashboard Components

#### 1. Real-Time Monitoring
- **Live GPS Events**: See drivers moving in real-time
- **Agent Activities**: Monitor what each agent is doing
- **Performance Metrics**: Track system performance and accuracy

#### 2. Agent Control Panel
- **Enable/Disable Agents**: Control which agents are active
- **Agent Settings**: Adjust sensitivity and thresholds
- **Manual Triggers**: Test agents with custom scenarios

#### 3. Analytics View
- **Delivery Performance**: Track average delivery times
- **Agent Effectiveness**: Measure prediction accuracy
- **System Health**: Monitor resource usage and errors

### Using the Interface

#### Navigation
```
📊 Dashboard Home
   ├── 🗺️ Live Map View
   ├── 📈 Performance Metrics
   ├── ⚙️ Agent Configuration
   ├── 🔍 Event Explorer
   └── 📋 System Logs
```

#### Key Features

**Live Map Visualization**:
- Real-time driver locations
- Order pickup and delivery points
- Traffic conditions overlay
- Optimized routes display

**Agent Status Indicators**:
- 🟢 Active and processing
- 🟡 Idle but ready
- 🔴 Error or disabled
- ⚪ Unknown status

**Performance Dashboard**:
- ETA prediction accuracy
- Route optimization savings
- Driver utilization rates
- System response times

## 🤖 Working with Agents

### Agent Types and Usage

#### ⏱️ ETA Prediction Agent
**What it does**: Calculates accurate delivery time estimates

**When to use**:
- Customer inquiry about delivery time
- Planning delivery schedules
- Optimizing restaurant preparation timing

**Example interaction**:
```bash
# Query ETA for specific order
curl -X POST http://localhost:8000/api/v1/agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the ETA for order abc123?",
    "context": {"order_id": "abc123", "driver_id": "driver_456"}
  }'
```

#### 🗺️ Route Optimization Agent
**What it does**: Finds the fastest delivery routes

**When to use**:
- Heavy traffic conditions
- Multiple delivery stops
- Emergency route changes

**Example interaction**:
```bash
# Request route optimization
curl -X POST http://localhost:8000/api/v1/agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Optimize route for driver in Vila Olimpia with heavy traffic",
    "context": {"driver_id": "driver_456", "traffic_level": "heavy"}
  }'
```

#### 🎯 Driver Allocation Agent
**What it does**: Assigns optimal drivers to new orders

**When to use**:
- New order placement
- Driver reassignment needed
- Load balancing during peak hours

**Example interaction**:
```bash
# Request driver allocation
curl -X POST http://localhost:8000/api/v1/agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Assign best driver for order in Itaim Bibi",
    "context": {"pickup_location": "Itaim_Bibi", "order_priority": "high"}
  }'
```

### Agent Communication

#### Natural Language Interface
The agents understand natural language queries:
- "How long will order 123 take to deliver?"
- "Find a faster route to avoid traffic on Marginal Pinheiros"
- "Which driver should handle the urgent order in Vila Madalena?"

#### Structured API Calls
For programmatic access, use the structured API:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/agent/process",
    json={
        "message": "Calculate ETA for current orders",
        "context": {"filter": "active_orders"},
        "agent_preference": "eta_prediction"
    }
)
```

## 📊 Monitoring and Analytics

### Real-Time Metrics

#### Agent Performance
- **Response Time**: Average time for agent to process requests
- **Accuracy**: Percentage of correct predictions/recommendations
- **Availability**: Uptime and reliability statistics

#### Delivery Metrics  
- **Average ETA Accuracy**: How close predictions are to actual times
- **Route Optimization Savings**: Time/distance saved through optimizations
- **Driver Utilization**: Percentage of time drivers are efficiently used

### Historical Analysis

#### Delivery Performance Trends
```bash
# Access performance data via API
curl "http://localhost:8000/api/v1/analytics/performance?days=7"
```

#### Agent Effectiveness Reports
- Weekly accuracy summaries
- Traffic pattern analysis
- Peak hour performance data

## 🔧 Configuration and Customization

### Agent Settings

#### ETA Prediction Tuning
```python
# Adjust prediction sensitivity
ETA_SETTINGS = {
    "traffic_weight": 0.7,      # Impact of traffic on ETA
    "weather_weight": 0.2,      # Impact of weather
    "driver_performance": 0.1,   # Driver skill factor
    "confidence_threshold": 0.8  # Minimum confidence to report
}
```

#### Route Optimization Parameters
```python
# Route optimization preferences
ROUTE_SETTINGS = {
    "avoid_highways": False,     # Prefer surface streets
    "minimize_time": True,       # Optimize for speed vs distance
    "traffic_threshold": 0.6,    # When to reroute due to traffic
    "update_frequency": 300      # Route recalculation interval (seconds)
}
```

### User Preferences

#### Dashboard Customization
- **Refresh Intervals**: Set how often data updates (5s, 30s, 1m, 5m)
- **Map Zoom Level**: Default zoom for geographic displays
- **Notification Settings**: Which events trigger alerts
- **Color Schemes**: Light/dark mode, accessibility options

#### Alert Configuration
```python
# Customize alert thresholds
ALERT_SETTINGS = {
    "eta_deviation_threshold": 10,    # Minutes before alerting
    "traffic_severity": "moderate",   # Minimum severity to alert
    "driver_response_timeout": 5,     # Minutes before driver timeout alert
    "system_error_level": "warning"   # Minimum error level to report
}
```

## 🚨 Troubleshooting

### Common Issues

#### Agent Not Responding
**Symptoms**: Agent shows as inactive or doesn't process requests
**Solutions**:
1. Check agent health status in dashboard
2. Verify database connections
3. Restart specific agent: `python scripts/restart_agent.py --type eta`

#### Inaccurate Predictions  
**Symptoms**: ETA predictions are consistently wrong
**Solutions**:
1. Check traffic data API connectivity
2. Verify GPS data quality
3. Adjust prediction model parameters

#### Dashboard Loading Issues
**Symptoms**: Dashboard is slow or doesn't load
**Solutions**:
1. Check Kafka connectivity: `python scripts/test_kafka.py`
2. Verify Redis connection: `redis-cli ping`
3. Restart dashboard: `./run_dashboard.sh`

### System Health Checks

#### Automated Diagnostics
```bash
# Run comprehensive system check
python scripts/health_check.py

# Check specific components
python scripts/health_check.py --component agents
python scripts/health_check.py --component database
python scripts/health_check.py --component kafka
```

#### Manual Verification
```bash
# Test agent responsiveness
curl http://localhost:8000/health

# Check database connectivity  
python -c "from src.utils.database_connections import test_connections; test_connections()"

# Verify Kafka topics
kafka-topics.sh --list --bootstrap-server localhost:9092
```

## 📞 Support and Resources

### Getting Help

#### Log Files
- **Agent Logs**: `logs/agents/`
- **System Logs**: `logs/system/`
- **Error Logs**: `logs/errors/`

#### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python src/main.py
```

#### Performance Profiling
```bash
# Profile agent performance
python scripts/profile_agents.py --duration 300
```

### Best Practices

#### Optimal Usage Patterns
1. **Monitor Regularly**: Check dashboard daily for system health
2. **Update Configurations**: Adjust agent settings based on performance
3. **Maintain Data Quality**: Ensure GPS and traffic data feeds are reliable
4. **Plan for Peak Hours**: Scale resources during high-demand periods

#### Performance Tips
- Use agent-specific endpoints for better response times
- Cache frequently accessed data in Redis
- Monitor and optimize database query performance
- Set appropriate timeout values for external API calls

### Advanced Features

#### Custom Scenarios
Create custom test scenarios to validate agent behavior:
```bash
# Generate test scenarios
python scripts/generate_scenarios.py --count 100 --type peak_hour

# Run scenario validation
python scripts/validate_agents.py --scenario peak_hour
```

#### Integration Examples
- **Restaurant Integration**: Connect with POS systems for prep time updates
- **Customer Notifications**: Send real-time ETA updates via SMS/email
- **Driver Mobile App**: Integrate route optimizations with driver navigation

This user guide provides everything you need to effectively use and monitor the UberEats Multi-Agent System.