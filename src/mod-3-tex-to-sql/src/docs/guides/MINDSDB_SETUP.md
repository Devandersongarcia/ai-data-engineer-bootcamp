# MindsDB Environment Setup Guide

**Complete setup guide for the MindsDB multi-agent system with specialized AI agents in under 10 minutes.**

## 🎯 Overview

The MindsDB Environment (`src/mindsdb/`) is optimized for:
- 👥 **Multi-Agent System**: 4 specialized AI agents with domain expertise
- 🔄 **Agent-to-Agent Communication**: Cross-database correlation and analysis
- 🧠 **Advanced AI**: MindsDB native integration with specialized agents
- 🇧🇷 **Brazilian Tax Expertise**: ICMS, ISS, PIS/COFINS compliance automation

## 🚀 Quick Setup

### 1. Prerequisites Check
```bash
# Verify Python version (3.9+ required)
python --version

# Check MindsDB server is running
curl -X GET http://127.0.0.1:47334/api/status
# Should return: {"status": "ok"}

# Verify you have access to the project directory
ls -la src/mindsdb/
```

### 2. Install MindsDB Server

#### Option 1: Python Installation (Recommended)
```bash
# Install MindsDB
pip install mindsdb

# Start MindsDB server
python -m mindsdb
```

#### Option 2: Docker Installation
```bash
# Run MindsDB in Docker
docker run -p 47334:47334 mindsdb/mindsdb

# Or with persistent data
docker run -p 47334:47334 -v mindsdb_data:/root/mindsdb mindsdb/mindsdb
```

### 3. Install Application Dependencies
```bash
cd src/mindsdb
pip install -r requirements.txt
```

Expected output:
```
Successfully installed mindsdb_sdk-1.8.0 streamlit-1.28.0 pandas-2.0.0 ...
```

### 4. Environment Configuration

Create your `.env` file:
```bash
cd src/mindsdb

# Create environment file
cat > .env << EOF
# MindsDB Configuration (Required)
MINDSDB_SERVER_URL=http://127.0.0.1:47334
AGENT_NAME=brasil_invoice_expert

# Database Credentials (Pre-configured for development)
POSTGRES_HOST=maglev.proxy.rlwy.net
POSTGRES_PORT=54891
POSTGRES_DATABASE=ubereats
POSTGRES_USER=postgres
POSTGRES_PASSWORD=XgfyZnwLEDuSDPAmMJchvdlpSKwpqRTb

# OpenAI Configuration (Required)
OPENAI_API_KEY=your-openai-api-key-here

# Optional Configurations
QDRANT_URL=your-qdrant-url
QDRANT_API_KEY=your-qdrant-key
LOG_LEVEL=INFO
APP_TITLE=Brasil Invoice Expert
EOF
```

### 5. MindsDB Agent Setup

**Step 5.1: Access MindsDB Editor**
```bash
# Open MindsDB Editor in browser
open http://127.0.0.1:47334
```

**Step 5.2: Create Database Connections**
Copy and execute from `sql/setup_template.sql`:
```sql
-- PostgreSQL Connection
CREATE DATABASE postgres_ubereats
WITH ENGINE = 'postgres',
PARAMETERS = {
    "host": "maglev.proxy.rlwy.net",
    "port": 54891,
    "database": "ubereats", 
    "user": "postgres",
    "password": "XgfyZnwLEDuSDPAmMJchvdlpSKwpqRTb"
};

-- MongoDB Connection
CREATE DATABASE ubereats_catalog
WITH ENGINE = 'mongodb',
PARAMETERS = {
    "host": "mongodb+srv://ubereatsgen:123456A%40@owshq-owa.2g5zw.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true",
    "database": "ubereats_catalog"
};

-- Supabase Connection
CREATE DATABASE supabase_db
WITH ENGINE = 'supabase',
PARAMETERS = {
    "host": "db.gpnfdkwklkfwrryetsgg.supabase.co",
    "port": 5432,
    "database": "postgres",
    "user": "postgres", 
    "password": "sb_secret__CBIJRe_kP8LvAaIiQGqSg_y2EjY_Tv"
};
```

**Step 5.3: Create Multi-Agent System**
Execute the complete multi-agent setup from `sql/multi_agent_setup.sql` (replace YOUR_OPENAI_KEY):
```sql
-- PostgreSQL Agent (Tax Compliance Specialist)
CREATE AGENT agent_postgres_transactions
USING
    model = 'gpt-4o-mini',
    provider = 'openai',
    openai_api_key = 'YOUR_OPENAI_KEY',
    skills = ['knowledge_base'],
    database = 'postgres_ubereats';

-- MongoDB Agent (Catalog Specialist)  
CREATE AGENT agent_mongo_catalog
USING
    model = 'gpt-4o-mini', 
    provider = 'openai',
    openai_api_key = 'YOUR_OPENAI_KEY',
    skills = ['knowledge_base'],
    database = 'ubereats_catalog';

-- Supabase Agent (Real-time Specialist)
CREATE AGENT agent_supabase_realtime
USING
    model = 'gpt-4o-mini',
    provider = 'openai', 
    openai_api_key = 'YOUR_OPENAI_KEY',
    skills = ['knowledge_base'],
    database = 'supabase_db';

-- Master Coordinator (Multi-Agent Orchestrator)
CREATE AGENT agent_ubereats_coordinator
USING
    model = 'gpt-4o-mini',
    provider = 'openai',
    openai_api_key = 'YOUR_OPENAI_KEY',
    skills = ['knowledge_base'];
```

Verify agents were created:
```sql
SHOW AGENTS;
```

Expected result:
```
agent_postgres_transactions
agent_mongo_catalog  
agent_supabase_realtime
agent_ubereats_coordinator
```

### 6. Test Basic Setup
```bash
# Test MindsDB connection
python -c "
from core.mindsdb_client import connect
server = connect('http://127.0.0.1:47334')
print('✅ MindsDB connection successful')
"

# Test agent access
python -c "
from core.mindsdb_client import connect
server = connect('http://127.0.0.1:47334')
agent = server.agents.get('agent_ubereats_coordinator')
print('✅ Agent access successful')
"
```

### 7. Launch the Application
```bash
# Method 1: Using the launcher (Recommended)
python run_app.py

# Method 2: Direct Streamlit
streamlit run apps/chat_app.py --server.port 8502
```

Expected output:
```
🧠 Starting Brasil Invoice Expert Chat...
📁 App directory: /path/to/src/mindsdb
🚀 Running: streamlit run apps/chat_app.py --server.port 8502

  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8502
```

### 8. Verify Installation
1. Open http://localhost:8502 in your browser
2. You should see: "🧠🇧🇷 Brasil Invoice Expert Chat"
3. Connect to MindsDB in the sidebar
4. Try a sample query: "Análise fiscal por cidade"
5. Verify you get agent response with business insights

## 🎯 First Steps Tutorial

### Understanding the Multi-Agent System

#### 🏦 PostgreSQL Agent (`agent_postgres_transactions`)
**Expertise**: Financial transactions and Brazilian tax compliance
- **Focus**: Invoices, payments, tax calculations, compliance analysis
- **Tables**: orders, invoices, payments, users, drivers
- **Specialization**: ICMS, ISS, PIS/COFINS calculations and reporting

#### 🍕 MongoDB Agent (`agent_mongo_catalog`)
**Expertise**: Restaurant catalog and product analysis
- **Focus**: Restaurant performance, menu analysis, market segmentation
- **Collections**: restaurants, products, menus, user profiles
- **Specialization**: Regional analysis, cuisine types, product trends

#### ⚡ Supabase Agent (`agent_supabase_realtime`)
**Expertise**: Real-time operational data
- **Focus**: Order status, delivery tracking, operational metrics
- **Tables**: order_status_tracking, active_orders, gps_tracking
- **Specialization**: Logistics optimization, delivery performance

#### 🎯 Master Coordinator (`agent_ubereats_coordinator`)
**Expertise**: Cross-database orchestration and comprehensive analysis
- **Focus**: Integrated insights, complex correlations, strategic reports
- **Capability**: Coordinates all agents, provides unified business intelligence
- **Specialization**: 360° business analysis, multi-agent workflow orchestration

### Understanding the Interface

**Sidebar Configuration**
- **MindsDB Server URL**: Pre-configured to local MindsDB instance
- **Agent Name**: Default uses coordinator agent for comprehensive analysis
- **Connection Status**: Green when connected, red when disconnected

**Main Chat Interface**
- **Query Input**: Natural language questions in Portuguese or English
- **Response Display**: Agent responses with SQL queries and business insights
- **Performance Metrics**: Token usage, cost tracking, response times

### Basic Query Testing

Try these queries to test your setup:

**1. Simple Fiscal Analysis**
```
Input: "Total de impostos por cidade"
Expected: PostgreSQL agent analysis with ICMS/ISS breakdown
```

**2. Restaurant Performance**
```
Input: "Top 5 restaurantes por faturamento"
Expected: Coordinator combining catalog and transaction data
```

**3. Real-time Operations**
```
Input: "Status dos pedidos em preparo"
Expected: Supabase agent with operational data
```

**4. Complex Multi-Agent Analysis**
```
Input: "Relatório executivo completo de compliance fiscal"
Expected: Coordinator orchestrating all agents for comprehensive report
```

### Multi-Agent System Testing

**Test Individual Agents**
In MindsDB Editor, test each agent:
```sql
-- PostgreSQL Agent
SELECT * FROM agent_postgres_transactions 
WHERE question = 'Total de impostos recolhidos'
LIMIT 1;

-- MongoDB Agent  
SELECT * FROM agent_mongo_catalog
WHERE question = 'Restaurantes com produtos vegetarianos'
LIMIT 1;

-- Supabase Agent
SELECT * FROM agent_supabase_realtime
WHERE question = 'Pedidos ativos no sistema'
LIMIT 1;

-- Master Coordinator
SELECT * FROM agent_ubereats_coordinator
WHERE question = 'Análise integrada de performance'
LIMIT 1;
```

## 🔧 Configuration Details

### Essential Settings

**MindsDB Connection** (Required)
- **URL**: http://127.0.0.1:47334 (local MindsDB server)
- **Agent**: brasil_invoice_expert or agent_ubereats_coordinator
- **Timeout**: 30 seconds for complex queries

**OpenAI API Key** (Required)
- Get from: https://platform.openai.com/api-keys
- Format: `sk-proj-...` or `sk-...`
- Usage: Embedded in agent configurations during setup

**Database Connections** (Pre-configured)
- **PostgreSQL**: Railway.app hosted database
- **MongoDB**: MongoDB Atlas cluster
- **Supabase**: Real-time database instance
- All connections read-only for security

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MINDSDB_SERVER_URL` | ✅ Yes | http://127.0.0.1:47334 | MindsDB server endpoint |
| `AGENT_NAME` | ✅ Yes | brasil_invoice_expert | Default agent name |
| `OPENAI_API_KEY` | ✅ Yes | None | OpenAI API authentication |
| `POSTGRES_HOST` | No | Pre-configured | PostgreSQL server host |
| `QDRANT_URL` | No | None | Vector database URL |
| `LOG_LEVEL` | No | INFO | Logging verbosity |
| `APP_TITLE` | No | Brasil Invoice Expert | Application title |

## 🐛 Troubleshooting

### Common Setup Issues

**"MindsDB server not accessible"**
```bash
# Check if MindsDB is running
curl -X GET http://127.0.0.1:47334/api/status

# Start MindsDB if needed
python -m mindsdb

# Or using Docker
docker run -p 47334:47334 mindsdb/mindsdb
```

**"Agent not found"**
```sql
-- Check existing agents
SHOW AGENTS;

-- If empty, run the setup SQL files:
-- 1. sql/setup_template.sql (database connections)
-- 2. sql/multi_agent_setup.sql (agent creation)
```

**"Database connection failed"**
```bash
# Test individual connections in MindsDB Editor
SELECT * FROM postgres_ubereats.orders LIMIT 1;
SELECT * FROM ubereats_catalog.restaurants LIMIT 1;
SELECT * FROM supabase_db.order_status_tracking LIMIT 1;
```

**"OpenAI API key invalid"**
```bash
# Verify API key format
echo $OPENAI_API_KEY
# Should start with 'sk-proj-' or 'sk-'

# Test API key validity
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

**"Import errors"**
```bash
# Ensure you're in the correct directory
pwd  # Should show: .../src/mindsdb

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

### Performance Issues

**Slow agent responses**
- Check internet connection (agents call OpenAI API)
- Try simpler questions first
- Monitor token usage in the interface
- Check MindsDB server logs

**Connection timeouts**
- Increase timeout in settings: `CONNECTION_TIMEOUT=60`
- Check network connectivity to databases
- Verify agent configuration in MindsDB

### Getting Help

**Check logs**
```bash
# Application logs
tail -f logs/brasil_invoice_expert.log

# MindsDB server logs
# Check MindsDB console output
```

**Run diagnostics**
```bash
# Test configuration
python -c "
from config.settings import get_settings
s = get_settings()
print(f'MindsDB URL: {s.mindsdb_server_url}')
print(f'Agent: {s.agent_name}')
print(f'OpenAI Key: {s.openai_api_key[:10]}...')
"

# Test MindsDB client
python -c "
from core.mindsdb_client import connect
try:
    server = connect()
    print('✅ MindsDB client working')
except Exception as e:
    print(f'❌ Client error: {e}')
"
```

## 🎯 Next Steps

### Basic Usage
1. **Learn the agents**: Understand each agent's specialty
2. **Practice queries**: Try different question types
3. **Monitor performance**: Watch token usage and costs

### Advanced Features
1. **Multi-agent workflows**: Complex cross-database analysis
2. **Custom agents**: Create specialized agents for your needs
3. **A2A coordination**: Agent-to-Agent communication patterns

### Business Applications
1. **Tax compliance**: Brazilian fiscal analysis automation
2. **Business intelligence**: Restaurant performance insights
3. **Operational monitoring**: Real-time business metrics

## 📊 Agent Performance Metrics

### Response Time Benchmarks
| Query Type | Response Time | Agent Used |
|------------|---------------|------------|
| **Simple Tax Queries** | 2-4 seconds | PostgreSQL Agent |
| **Catalog Queries** | 2-3 seconds | MongoDB Agent |
| **Real-time Queries** | 1-3 seconds | Supabase Agent |
| **Complex Analysis** | 5-10 seconds | Coordinator + All |

### Resource Usage
- **Memory**: 1-3GB depending on agent usage
- **CPU**: 2-4 cores for multi-agent processing
- **Network**: High (multiple API calls, database connections)
- **Storage**: 200MB + log files

## 🛡️ Security Considerations

### Multi-Agent Security Checklist
- [ ] **API Keys**: Secure OpenAI key storage in agent configs
- [ ] **Database Access**: Read-only permissions for all connections
- [ ] **Agent Validation**: Verify agent existence before queries
- [ ] **Input Sanitization**: Natural language input validation
- [ ] **Audit Logging**: Complete agent interaction logging
- [ ] **Network Security**: Secure connections to all data sources

### Security Best Practices
```bash
# Secure environment variables
chmod 600 .env

# Validate agents regularly
curl -X GET http://127.0.0.1:47334/api/agents

# Monitor agent usage
tail -f logs/brasil_invoice_expert.log
```

## 📚 Additional Resources

- **[Features Documentation](../MINDSDB_FEATURES.md)** - Complete feature overview
- **[Multi-Agent Guide](../architecture/MULTI_AGENT_ARCHITECTURE.md)** - Advanced architecture details
- **[API Reference](../api/MINDSDB_API.md)** - Development documentation
- **[Archive Documentation](../../mindsdb/docs/archive/)** - Historical guides and examples

## 🤝 Need Help?

**Common Questions**
- Check agent configurations in MindsDB Editor: http://127.0.0.1:47334
- Review SQL setup files in `sql/` directory
- Test individual agents before complex workflows

**Issues or Bugs**
- Verify MindsDB server is running and accessible
- Check agent creation in MindsDB Editor with `SHOW AGENTS;`
- Validate database connections with sample queries

**Feature Requests**
- Explore advanced agent architectures in archive documentation
- Consider A2A coordination patterns for complex workflows
- Review multi-agent examples for inspiration

---

## 🎯 Multi-Agent Ready

**Advanced AI Architecture**
- ✅ **Multi-Agent System**: 4 specialized agents with domain expertise
- ✅ **Agent-to-Agent Communication**: Cross-database intelligence
- ✅ **Brazilian Tax Expertise**: ICMS, ISS, PIS/COFINS compliance
- ✅ **Real-time Analytics**: Live operational data integration

**Production Features**
- ✅ **Custom MindsDB Client**: Bypass SDK limitations
- ✅ **Enterprise Security**: Agent validation and error handling
- ✅ **Performance Monitoring**: Token usage and cost optimization
- ✅ **Structured Logging**: Comprehensive audit and debugging

**Business Value**
- ✅ **Self-Service Analytics**: Natural language business intelligence
- ✅ **Regulatory Compliance**: Brazilian tax law automation
- ✅ **Operational Efficiency**: Real-time business insights
- ✅ **Cross-Database Intelligence**: Unified data analysis

---

**🚀 Ready to explore?** Your MindsDB multi-agent system should now be fully operational. Try asking: "Análise completa de compliance fiscal dos restaurantes" and see the advanced multi-agent coordination in action!