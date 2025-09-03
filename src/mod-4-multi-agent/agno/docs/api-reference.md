# 🔌 API Reference

## Overview
The UberEats Multi-Agent System provides a RESTful API for interacting with agents, monitoring system health, and accessing real-time data.

**Base URL**: `http://localhost:8000`  
**API Version**: `v1`

## 🔐 Authentication

### Bearer Token (Optional)
```bash
curl -H "Authorization: Bearer your-token-here" \
     http://localhost:8000/api/v1/agent/process
```

### Rate Limiting
- **Default**: 100 requests per minute per IP
- **Authenticated**: 1000 requests per minute per token

## 🤖 Agent Endpoints

### Process Agent Request
Execute an agent request with natural language or structured input.

**Endpoint**: `POST /api/v1/agent/process`

**Request Body**:
```json
{
  "message": "What is the ETA for order abc123?",
  "context": {
    "order_id": "abc123",
    "driver_id": "driver_456"
  },
  "customer_id": "customer_789",
  "session_id": "session_101",
  "priority": "normal",
  "agent_preference": "eta_prediction"
}
```

**Response**:
```json
{
  "success": true,
  "agent_type": "eta_prediction",
  "response": "Order abc123 will be delivered in approximately 23 minutes",
  "confidence": 0.89,
  "data": {
    "pickup_eta": 8.5,
    "delivery_eta": 23.2,
    "factors": ["traffic", "weather", "driver_performance"]
  },
  "session_id": "session_101",
  "processing_time": 1.2
}
```

**Parameters**:
- `message` (required): Natural language request or command
- `context` (optional): Additional context data
- `customer_id` (optional): Customer identifier for personalization
- `session_id` (optional): Session tracking identifier
- `priority` (optional): Request priority (`low`, `normal`, `high`, `critical`)
- `agent_preference` (optional): Preferred agent type

**Example Requests**:

```bash
# ETA Prediction
curl -X POST http://localhost:8000/api/v1/agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Calculate delivery ETA for order with heavy traffic",
    "context": {"order_id": "ord_123", "traffic_level": "heavy"},
    "agent_preference": "eta_prediction"
  }'

# Route Optimization  
curl -X POST http://localhost:8000/api/v1/agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find fastest route avoiding Marginal Pinheiros",
    "context": {"driver_id": "drv_456", "avoid_highways": ["marginal"]},
    "agent_preference": "route_optimization"
  }'

# Driver Allocation
curl -X POST http://localhost:8000/api/v1/agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Assign best available driver in Vila Madalena",
    "context": {"pickup_location": "Vila_Madalena", "order_priority": "high"},
    "agent_preference": "driver_allocation"
  }'
```

### Stream Agent Response
Get real-time streaming response from agents for long-running operations.

**Endpoint**: `POST /api/v1/agent/stream`

**Response**: Server-Sent Events (SSE) stream
```
data: {"type": "start", "agent": "route_optimization"}
data: {"type": "progress", "step": "analyzing_traffic", "progress": 0.3}
data: {"type": "result", "route": [...], "time_savings": 12.5}
data: {"type": "complete", "total_time": 3.2}
```

## 🔄 Workflow Endpoints

### Execute Workflow
Run complex multi-agent workflows for sophisticated scenarios.

**Endpoint**: `POST /api/v1/workflow/execute`

**Request Body**:
```json
{
  "request_type": "delivery_optimization",
  "data": {
    "orders": ["ord_1", "ord_2", "ord_3"],
    "drivers": ["drv_a", "drv_b"],
    "constraints": {
      "max_delivery_time": 45,
      "priority_orders": ["ord_1"]
    }
  },
  "session_id": "workflow_session_123",
  "priority": "high",
  "workflow_options": {
    "enable_advanced_coordination": true,
    "max_iterations": 5
  }
}
```

**Response**:
```json
{
  "workflow_id": "wf_789",
  "status": "completed", 
  "results": {
    "optimized_assignments": [...],
    "total_time_saved": 18.7,
    "efficiency_improvement": 0.23
  },
  "execution_time": 5.4,
  "agents_involved": ["eta_prediction", "route_optimization", "driver_allocation"]
}
```

## 📊 Monitoring Endpoints

### System Health
Check overall system health and component status.

**Endpoint**: `GET /api/v1/health`

**Response**:
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "uptime": 86400,
  "components": {
    "database": {"status": "healthy", "response_time": 45},
    "redis": {"status": "healthy", "connections": 8},
    "kafka": {"status": "healthy", "topics": 5},
    "agents": {"status": "healthy", "active": 4}
  },
  "metrics": {
    "total_requests": 15420,
    "average_response_time": 1.2,
    "success_rate": 0.987
  }
}
```

### Agent Status
Get detailed status of all agents.

**Endpoint**: `GET /api/v1/agents/status`

**Response**:
```json
{
  "agents": {
    "eta_prediction": {
      "status": "active",
      "requests_processed": 234,
      "average_confidence": 0.89,
      "last_activity": "2024-08-28T10:30:00Z"
    },
    "route_optimization": {
      "status": "active", 
      "routes_optimized": 89,
      "average_time_savings": 12.3,
      "last_activity": "2024-08-28T10:29:45Z"
    },
    "driver_allocation": {
      "status": "active",
      "allocations_made": 156,
      "average_response_time": 0.8,
      "last_activity": "2024-08-28T10:30:15Z"
    },
    "alert_management": {
      "status": "active",
      "alerts_processed": 12,
      "anomalies_detected": 3,
      "last_activity": "2024-08-28T10:25:30Z"
    }
  }
}
```

### Performance Metrics
Get detailed performance metrics and analytics.

**Endpoint**: `GET /api/v1/metrics`

**Query Parameters**:
- `period`: Time period (`1h`, `24h`, `7d`, `30d`)
- `agent_type`: Filter by specific agent
- `format`: Response format (`json`, `prometheus`)

**Response**:
```json
{
  "period": "24h",
  "summary": {
    "total_requests": 5420,
    "successful_requests": 5354,
    "failed_requests": 66,
    "success_rate": 0.988,
    "average_response_time": 1.23
  },
  "agent_performance": {
    "eta_prediction": {
      "requests": 2340,
      "accuracy": 0.891,
      "avg_response_time": 0.95
    },
    "route_optimization": {
      "requests": 1890,
      "time_savings_avg": 11.7,
      "avg_response_time": 1.85
    }
  },
  "system_metrics": {
    "cpu_usage": 0.35,
    "memory_usage": 0.68,
    "disk_usage": 0.23
  }
}
```

## 📈 Analytics Endpoints

### Delivery Analytics
Get delivery performance analytics and insights.

**Endpoint**: `GET /api/v1/analytics/delivery`

**Response**:
```json
{
  "summary": {
    "total_deliveries": 1250,
    "average_delivery_time": 32.4,
    "on_time_rate": 0.923,
    "customer_satisfaction": 4.6
  },
  "performance_trends": {
    "eta_accuracy_trend": [0.85, 0.87, 0.89, 0.91],
    "delivery_time_trend": [35.2, 34.1, 32.8, 32.4]
  },
  "geographic_performance": {
    "Vila_Olimpia": {"avg_time": 28.5, "accuracy": 0.94},
    "Itaim_Bibi": {"avg_time": 31.2, "accuracy": 0.89}
  }
}
```

### Traffic Analytics
Get traffic pattern analysis and predictions.

**Endpoint**: `GET /api/v1/analytics/traffic`

**Response**:
```json
{
  "current_conditions": {
    "overall_index": 0.67,
    "peak_areas": ["Marginal_Pinheiros", "Av_Paulista"],
    "optimal_routes": ["Via_Expressa", "Tunnel_Routes"]
  },
  "predictions": {
    "next_hour": {"expected_index": 0.72, "confidence": 0.89},
    "peak_hours": ["18:00-20:00", "08:00-09:30"]
  },
  "historical_patterns": {
    "weekday_avg": [0.3, 0.4, 0.6, 0.8, 0.7, 0.5, 0.4],
    "weekend_avg": [0.2, 0.3, 0.5, 0.6, 0.5, 0.4, 0.3]
  }
}
```

## 🔧 Configuration Endpoints

### Update Agent Configuration
Modify agent settings and parameters dynamically.

**Endpoint**: `PUT /api/v1/agents/{agent_type}/config`

**Request Body**:
```json
{
  "settings": {
    "confidence_threshold": 0.85,
    "timeout": 30,
    "retry_attempts": 3
  },
  "parameters": {
    "traffic_weight": 0.7,
    "weather_impact": 0.2
  }
}
```

### Get System Configuration
Retrieve current system configuration.

**Endpoint**: `GET /api/v1/config`

**Response**:
```json
{
  "system": {
    "max_concurrent_agents": 50,
    "request_timeout": 30,
    "log_level": "INFO"
  },
  "agents": {
    "eta_prediction": {...},
    "route_optimization": {...}
  },
  "integrations": {
    "kafka_enabled": true,
    "redis_enabled": true,
    "langfuse_enabled": true
  }
}
```

## 🚨 Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "AGENT_ERROR",
    "message": "Agent processing failed",
    "details": "Specific error details here",
    "request_id": "req_123456",
    "timestamp": "2024-08-28T10:30:00Z"
  }
}
```

### Common Error Codes
- `400`: Bad Request - Invalid input parameters
- `401`: Unauthorized - Missing or invalid authentication
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Endpoint or resource not found
- `422`: Unprocessable Entity - Validation errors
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error - System error
- `503`: Service Unavailable - System maintenance or overload

### Validation Errors
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": [
      {
        "field": "message",
        "error": "Message cannot be empty"
      },
      {
        "field": "priority", 
        "error": "Priority must be one of: low, normal, high, critical"
      }
    ]
  }
}
```

## 📚 SDK and Examples

### Python SDK Example
```python
import requests

class UberEatsAgentsAPI:
    def __init__(self, base_url="http://localhost:8000", token=None):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def process_agent_request(self, message, **kwargs):
        payload = {"message": message, **kwargs}
        response = requests.post(
            f"{self.base_url}/api/v1/agent/process",
            json=payload,
            headers=self.headers
        )
        return response.json()
    
    def get_system_health(self):
        response = requests.get(f"{self.base_url}/api/v1/health")
        return response.json()

# Usage
api = UberEatsAgentsAPI()
result = api.process_agent_request(
    message="Calculate ETA for order abc123",
    context={"order_id": "abc123"},
    agent_preference="eta_prediction"
)
```

### JavaScript SDK Example
```javascript
class UberEatsAgentsAPI {
  constructor(baseUrl = 'http://localhost:8000', token = null) {
    this.baseUrl = baseUrl;
    this.headers = {'Content-Type': 'application/json'};
    if (token) {
      this.headers['Authorization'] = `Bearer ${token}`;
    }
  }

  async processAgentRequest(message, options = {}) {
    const response = await fetch(`${this.baseUrl}/api/v1/agent/process`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({message, ...options})
    });
    return response.json();
  }
}

// Usage
const api = new UberEatsAgentsAPI();
const result = await api.processAgentRequest(
  'Find fastest route to Vila Madalena',
  {agent_preference: 'route_optimization'}
);
```

This API reference provides comprehensive coverage of all available endpoints for integrating with the UberEats Multi-Agent System.