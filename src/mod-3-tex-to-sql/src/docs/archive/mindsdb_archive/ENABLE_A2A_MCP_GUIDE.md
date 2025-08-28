# 🔗 Enable A2A & MCP in MindsDB - Setup Guide

## 🎯 **What are A2A and MCP?**

- **A2A (Agent-to-Agent)**: Allows MindsDB agents to communicate and collaborate with each other
- **MCP (Model Context Protocol)**: Enables MindsDB to work with external MCP-compatible applications for federated data queries

---

## 🚀 **Current Setup Analysis**

Your MindsDB is running as a **local Python process** (not Docker). To enable A2A and MCP, you have several options:

---

## 💻 **Option 1: Local Python Setup (Recommended)**

### **Enable via Environment Variables:**
```bash
# Set the APIs to include MCP and A2A
export MINDSDB_APIS='http,mysql,mcp,a2a'

# Optional: Set MCP access token for security
export MINDSDB_MCP_ACCESS_TOKEN='your_secure_token_here'

# Restart MindsDB to apply changes
pkill -f mindsdb
python -m mindsdb --api=http,mysql,mcp,a2a
```

### **Or start with specific API flags:**
```bash
python -m mindsdb --api=mcp,a2a,http,mysql
```

---

## 🐳 **Option 2: Docker Setup (Full Featured)**

### **Stop current MindsDB process:**
```bash
# Find and stop current MindsDB
ps aux | grep mindsdb
kill <PID_OF_MINDSDB_PROCESS>
```

### **Start MindsDB with Docker:**
```bash
# Without authentication
docker run --name mindsdb_container \
  -e MINDSDB_APIS=http,mysql,mcp,a2a \
  -p 47334:47334 -p 47335:47335 -p 47337:47337 -p 47338:47338 \
  mindsdb/mindsdb

# With authentication (recommended for production)
docker run --name mindsdb_container \
  -e MINDSDB_MCP_ACCESS_TOKEN=abc123 \
  -e MINDSDB_APIS=http,mysql,mcp,a2a \
  -p 47334:47334 -p 47335:47335 -p 47337:47337 -p 47338:47338 \
  mindsdb/mindsdb
```

### **Port Mapping:**
- **47334**: HTTP API (current)
- **47335**: MySQL API
- **47337**: MCP Server
- **47338**: A2A Communication

---

## 🔧 **Verification Steps**

### **1. Check APIs Status:**
```bash
curl http://127.0.0.1:47334/api/status
```

### **2. Test MCP Endpoint:**
```bash
curl http://127.0.0.1:47337/mcp/status
```

### **3. Test A2A Endpoint:**
```bash
curl http://127.0.0.1:47338/a2a/status
```

### **4. List Available MCP Tools:**
```bash
curl -X POST http://127.0.0.1:47337/mcp/tools \
  -H "Content-Type: application/json" \
  -d '{"method": "list_tools"}'
```

---

## 🤖 **A2A Usage Examples**

### **Agent-to-Agent Communication:**
```sql
-- Create an agent that can call other agents
CREATE AGENT coordinator_with_a2a
USING
    model = {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "api_key": "your_api_key"
    },
    data = {
        "agents": [
            "agent_postgres_transactions",
            "agent_mongo_catalog", 
            "agent_supabase_realtime"
        ]
    },
    prompt_template = 'Coordinator agent that can call other specialized agents:
    
    AVAILABLE AGENTS:
    - agent_postgres_transactions: For fiscal and transaction data
    - agent_mongo_catalog: For restaurant and product data
    - agent_supabase_realtime: For real-time operational data
    
    Use CALL AGENT syntax to delegate specialized queries to appropriate agents.
    
    Example: CALL AGENT agent_postgres_transactions("Calculate total taxes by city")
    ';
```

---

## 🔌 **MCP Usage Examples**

### **MCP Tools Available:**

#### **1. list_databases**
```bash
curl -X POST http://127.0.0.1:47337/mcp/query \
  -H "Content-Type: application/json" \
  -d '{
    "method": "list_databases"
  }'
```

#### **2. Federated Query**
```bash
curl -X POST http://127.0.0.1:47337/mcp/query \
  -H "Content-Type: application/json" \
  -d '{
    "method": "query",
    "params": {
      "query": "SELECT COUNT(*) FROM postgres_ubereats.orders"
    }
  }'
```

---

## 🏗️ **Architecture with A2A & MCP**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │    │   Your App      │    │  External Agent │
│    :47337       │    │   :47334        │    │    :47338       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                 MindsDB Core                                │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
    │  │ PostgreSQL  │  │  MongoDB    │  │     Supabase        │ │
    │  │   Agent     │  │   Agent     │  │     Agent           │ │
    │  └─────────────┘  └─────────────┘  └─────────────────────┘ │
    └─────────────────────────────────────────────────────────────┘
```

---

## 📋 **Step-by-Step Implementation**

### **Step 1: Stop Current MindsDB**
```bash
# Find MindsDB process
ps aux | grep mindsdb

# Stop it (replace 6542 with actual PID)
kill 6542
```

### **Step 2: Enable A2A & MCP**
```bash
# Method 1: Environment variables
export MINDSDB_APIS='http,mysql,mcp,a2a'
python -m mindsdb

# Method 2: Direct flag
python -m mindsdb --api=http,mysql,mcp,a2a
```

### **Step 3: Verify All APIs**
```bash
# Main API (should still work)
curl http://127.0.0.1:47334/api/status

# MCP API (new)
curl http://127.0.0.1:47337/mcp/status

# A2A API (new)  
curl http://127.0.0.1:47338/a2a/status

# MySQL API (new)
mysql -h 127.0.0.1 -P 47335 -u mindsdb -p
```

### **Step 4: Update Your Applications**
```python
# Update config/settings.py
MINDSDB_SERVER_URL = "http://127.0.0.1:47334"  # HTTP API
MINDSDB_MCP_URL = "http://127.0.0.1:47337"     # MCP API
MINDSDB_A2A_URL = "http://127.0.0.1:47338"     # A2A API
```

---

## 🎯 **Benefits After Enabling**

### **A2A Benefits:**
- ✅ **Agent Collaboration**: Coordinator can delegate to specialists
- ✅ **Complex Workflows**: Multi-step agent processes
- ✅ **Specialized Expertise**: Each agent focuses on their domain

### **MCP Benefits:**
- ✅ **External Integration**: Connect with MCP-compatible apps
- ✅ **Federated Queries**: Query across multiple data sources
- ✅ **Standardized Protocol**: Use industry-standard MCP interface

---

## ⚠️ **Important Notes**

1. **Data Persistence**: Your databases and agents will remain intact
2. **Port Requirements**: Ensure ports 47335, 47337, 47338 are available
3. **Firewall**: Allow traffic on new ports if running in production
4. **Authentication**: Consider setting `MINDSDB_MCP_ACCESS_TOKEN` for security

---

## 🧪 **Testing Your Setup**

```bash
# Test script to verify all APIs
#!/bin/bash
echo "Testing MindsDB APIs..."

echo "1. HTTP API:"
curl -s http://127.0.0.1:47334/api/status | jq '.mindsdb_version'

echo "2. MCP API:"
curl -s http://127.0.0.1:47337/mcp/status || echo "MCP not available"

echo "3. A2A API:"
curl -s http://127.0.0.1:47338/a2a/status || echo "A2A not available"

echo "4. Databases:"
curl -s -X POST "http://127.0.0.1:47334/api/sql/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "SHOW DATABASES;"}' | jq '.data'
```

---

**🚀 Ready to enable advanced MindsDB capabilities with A2A and MCP!** 🔗