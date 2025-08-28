# Multi-Agent Architecture Guide - Brasil Invoice Expert

Comprehensive guide to the advanced multi-agent system design and implementation.

## 🏗️ Architecture Overview

The Brasil Invoice Expert uses a sophisticated **4-agent specialized architecture** that replaces traditional single-agent limitations with coordinated domain expertise.

```
                    🎯 MASTER COORDINATOR
                   (agent_ubereats_coordinator)
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   🏦 POSTGRESQL        🍕 MONGODB         ⚡ SUPABASE
   TRANSACTIONS         CATALOG            REALTIME
   (Financial)          (Products)         (Operations)
```

## 👥 Agent Specialization

### 🏦 PostgreSQL Agent (`agent_postgres_transactions`)

**Domain**: Financial Transactions & Brazilian Tax Compliance

```sql
-- Agent Configuration
CREATE AGENT agent_postgres_transactions
USING
    model = {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "max_tokens": 800,
        "temperature": 0.1
    },
    data = {
        "tables": [
            "postgres_ubereats.orders",
            "postgres_ubereats.invoices", 
            "postgres_ubereats.payments",
            "postgres_ubereats.users"
        ]
    }
```

**Specialized Knowledge**
```python
fiscal_expertise = {
    "brazilian_taxes": {
        "ICMS": "17-18% state tax on goods (varies by state)",
        "ISS": "2-5% municipal tax on services (delivery fees)",
        "PIS_COFINS": "3.65% combined federal tax on revenue"
    },
    "compliance_tracking": {
        "invoice_statuses": ["issued", "paid", "cancelled", "refunded"],
        "cnpj_validation": "XX.XXX.XXX/XXXX-XX format",
        "fiscal_deadlines": "Monthly and quarterly reporting"
    },
    "financial_analysis": {
        "revenue_calculation": "By region, payment method, time period",
        "tax_optimization": "Identify savings opportunities", 
        "compliance_reporting": "Automated regulatory reports"
    }
}
```

**Example Queries**
- *"Total de impostos recolhidos por cidade"* → Tax collection by city
- *"Restaurantes com baixa eficiência fiscal"* → Tax efficiency analysis
- *"Análise de métodos de pagamento mais usados"* → Payment method trends

### 🍕 MongoDB Agent (`agent_mongo_catalog`)

**Domain**: Restaurant Catalog & Product Analysis

```javascript
// Agent Data Scope
collections = {
    "restaurants": {
        "fields": ["cnpj", "name", "city", "cuisine_type", "rating"],
        "purpose": "Restaurant master data and performance"
    },
    "products": {
        "fields": ["restaurant_id", "name", "price", "is_vegetarian"],
        "purpose": "Menu analysis and product trends"
    }
}
```

**Specialized Knowledge**
```python
catalog_expertise = {
    "restaurant_analysis": {
        "performance_metrics": "Rating, reviews, order volume",
        "regional_analysis": "City-based market performance",
        "cuisine_segmentation": "Brazilian, Italian, Mexican, French, Japanese"
    },
    "product_intelligence": {
        "menu_optimization": "Popular items, pricing analysis",
        "dietary_preferences": "Vegetarian, gluten-free, healthy options",
        "competitive_analysis": "Price comparison, offering gaps"
    },
    "market_insights": {
        "geographic_trends": "Regional cuisine preferences",
        "seasonal_patterns": "Menu item popularity cycles",
        "growth_opportunities": "Underserved markets, new concepts"
    }
}
```

**Example Queries**
- *"Top restaurantes por avaliação em cada cidade"* → Rating analysis by location
- *"Produtos mais caros por tipo de cozinha"* → Pricing analysis by cuisine
- *"Restaurantes com mais opções vegetarianas"* → Vegetarian offerings analysis

### ⚡ Supabase Agent (`agent_supabase_realtime`)

**Domain**: Real-time Operational Data

```sql
-- Real-time Tables
operational_data = {
    "order_status_tracking": {
        "fields": ["order_identifier", "status", "timestamp", "location"],
        "update_frequency": "Real-time",
        "purpose": "Live order monitoring"
    },
    "active_orders": {
        "status": "Reference table",
        "purpose": "Current operational state"
    }
}
```

**Specialized Knowledge**
```python
operational_expertise = {
    "status_monitoring": {
        "order_states": ["Preparing", "In Analysis", "Order Placed", "Accepted", "Delivered"],
        "location_tracking": "São Paulo metropolitan area",
        "performance_sla": "Delivery time benchmarks"
    },
    "logistics_optimization": {
        "delivery_routing": "GPS-based efficiency analysis",
        "capacity_planning": "Kitchen and delivery resource allocation",
        "bottleneck_identification": "Operational constraint analysis"
    },
    "real_time_insights": {
        "live_dashboards": "Current operational metrics",
        "predictive_alerts": "Proactive issue detection",
        "performance_trending": "Real-time KPI tracking"
    }
}
```

**Example Queries**
- *"Quantos pedidos estão em preparo agora?"* → Current preparation queue
- *"Status de entregas na última hora"* → Recent delivery performance
- *"Análise de tempo médio de entrega por região"* → Delivery efficiency metrics

### 🎯 Master Coordinator (`agent_ubereats_coordinator`)

**Domain**: Cross-database Orchestration & Business Intelligence

```python
# Coordination Capabilities
coordination_features = {
    "agent_delegation": "Route queries to appropriate specialists",
    "data_correlation": "Cross-database relationship mapping",
    "insight_synthesis": "Combine specialist analyses",
    "strategic_reporting": "Executive-level business intelligence"
}
```

**Advanced Workflows**
```python
class CoordinatorWorkflows:
    def complex_analysis(self, query: str):
        """Multi-step analysis coordination"""
        
        # 1. Query classification
        query_type = self.classify_query(query)
        
        # 2. Agent selection  
        required_agents = self.select_agents(query_type)
        
        # 3. Parallel execution
        specialist_results = await self.execute_parallel(
            required_agents, query
        )
        
        # 4. Data correlation
        correlated_data = self.correlate_results(
            specialist_results, 
            correlation_key="cnpj"
        )
        
        # 5. Synthesis
        return self.synthesize_insights(correlated_data)
```

**Cross-Database Correlation**
```sql
-- Example: Restaurant performance with tax efficiency
SELECT 
    r.name as restaurant_name,
    r.city,
    r.average_rating,
    COUNT(p.product_id) as menu_items,
    SUM(i.tax_amount) as total_taxes,
    AVG(i.total_amount) as avg_order_value
FROM ubereats_catalog.restaurants r
JOIN ubereats_catalog.products p ON r.restaurant_id = p.restaurant_id  
JOIN postgres_ubereats.orders o ON r.cnpj = o.restaurant_key
JOIN postgres_ubereats.invoices i ON o.order_id = i.order_key
WHERE i.invoice_status = 'paid'
GROUP BY r.name, r.city, r.average_rating
ORDER BY total_taxes DESC
LIMIT 20;
```

## 🔄 Multi-Agent Workflows

### Workflow 1: Simple Single-Agent Query

```
User: "Total de impostos por cidade"
         ↓
🎯 Coordinator Analysis
         ↓
   Classification: "fiscal_query"
         ↓  
🏦 PostgreSQL Agent
         ↓
Tax calculation by city with ICMS/ISS breakdown
         ↓
Formatted response with business insights
```

### Workflow 2: Cross-Database Correlation

```
User: "Restaurantes vegetarianos com melhor performance fiscal"
                    ↓
        🎯 Coordinator Analysis
                    ↓
    Classification: "cross_database_complex"
                    ↓
        ┌─────────────┴─────────────┐
        ▼                           ▼
🍕 MongoDB Agent              🏦 PostgreSQL Agent
"Find vegetarian              "Get tax compliance
restaurants"                  by restaurant CNPJ"
        ▼                           ▼
   [18 restaurants]            [Tax efficiency data]
        ▼                           ▼
        └─────────────┬─────────────┘
                      ▼
        🎯 Coordinator Correlation
        (Match via CNPJ = restaurant_key)
                      ▼
    Integrated analysis: Vegetarian restaurants 
    with best tax efficiency scores
```

### Workflow 3: Multi-Agent Executive Report

```
User: "Dashboard executivo completo"
                    ↓
        🎯 Coordinator Analysis
                    ↓
        Parallel Agent Execution
                    ↓
    ┌─────────────┬─────────────┬─────────────┐
    ▼             ▼             ▼             ▼
🏦 Financial   🍕 Catalog    ⚡ Operations  🎯 Synthesis
Analysis       Intelligence  Monitoring     & Insights
    ▼             ▼             ▼             ▼
Revenue &      Restaurant    Real-time      Strategic
Tax Data       Performance   Status         Recommendations
    ▼             ▼             ▼             ▼
    └─────────────┴─────────────┴─────────────┘
                      ▼
            Executive Dashboard
            - Financial KPIs
            - Market Performance  
            - Operational Metrics
            - Strategic Insights
```

## 🎯 Agent Selection Logic

### Automatic Query Classification

```python
class QueryClassifier:
    def __init__(self):
        self.classification_rules = {
            "fiscal_keywords": ["imposto", "taxa", "compliance", "fiscal"],
            "catalog_keywords": ["restaurante", "produto", "menu", "rating"],
            "operational_keywords": ["tempo real", "status", "entrega", "preparo"],
            "complex_keywords": ["dashboard", "relatório", "análise completa"]
        }
    
    def classify_query(self, query: str) -> str:
        """Determine optimal agent routing"""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in self.fiscal_keywords):
            return "postgres_agent"
        elif any(kw in query_lower for kw in self.catalog_keywords):
            return "mongo_agent"
        elif any(kw in query_lower for kw in self.operational_keywords):
            return "supabase_agent"
        elif any(kw in query_lower for kw in self.complex_keywords):
            return "coordinator_multi_agent"
        else:
            return "coordinator_default"
```

### Agent Performance Optimization

```python
class AgentPerformanceOptimizer:
    def __init__(self):
        self.agent_metrics = {
            "postgres_transactions": {
                "avg_response_time": 2.3,
                "success_rate": 0.94,
                "token_efficiency": 0.87
            },
            "mongo_catalog": {
                "avg_response_time": 1.8,
                "success_rate": 0.96,
                "token_efficiency": 0.92
            },
            "supabase_realtime": {
                "avg_response_time": 1.2,
                "success_rate": 0.98,
                "token_efficiency": 0.95
            }
        }
    
    def select_optimal_agent(self, query_type: str, priority: str = "balanced"):
        """Choose best agent based on performance criteria"""
        if priority == "speed":
            return min(agents, key=lambda x: x.avg_response_time)
        elif priority == "accuracy":
            return max(agents, key=lambda x: x.success_rate)
        elif priority == "cost":
            return max(agents, key=lambda x: x.token_efficiency)
```

## 🔧 Advanced Configuration

### Agent-to-Agent Communication Setup

```sql
-- Create A2A Coordinator for cross-database intelligence
CREATE AGENT a2a_coordinator
USING
    model = {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "max_tokens": 1200,
        "temperature": 0.2
    },
    data = {
        "tables": [
            "postgres_ubereats.orders",
            "postgres_ubereats.invoices", 
            "ubereats_catalog.restaurants",
            "ubereats_catalog.products"
        ]
    },
    prompt_template = 'A2A Coordinator specializing in cross-database correlation.
    
    CORRELATION KEY: restaurants.cnpj = orders.restaurant_key
    
    WORKFLOW:
    1. Analyze query complexity
    2. Delegate to specialist agents if needed
    3. Correlate results across databases
    4. Synthesize unified business intelligence
    
    RESPONSE: Integrated analysis with cross-database insights.';
```

### Custom Agent Development Template

```sql
-- Template for creating domain-specific agents
CREATE AGENT agent_custom_domain
USING
    model = {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "api_key": "your-secure-api-key",
        "max_tokens": 800,
        "temperature": 0.1
    },
    data = {
        "tables": ["your.database.tables"],
        "knowledge_bases": ["your_knowledge_base"]  -- Optional
    },
    prompt_template = 'Domain Expert for [Your Specialty].
    
    EXPERTISE: [Define domain knowledge]
    DATA: [Describe table schemas and relationships]
    BUSINESS_CONTEXT: [Explain business rules]
    
    RESPONSE_FORMAT: [Specify output format]
    MAX_WORDS: [Set response length limit]';
```

### Performance Tuning Configuration

```python
# Multi-agent system configuration
multi_agent_config = {
    "coordination_timeout": 60,  # seconds
    "parallel_execution": True,
    "agent_retry_attempts": 2,
    "cross_database_correlation": True,
    "response_caching": {
        "enabled": True,
        "ttl_seconds": 300,
        "max_entries": 100
    },
    "performance_monitoring": {
        "track_token_usage": True,
        "track_response_times": True,
        "track_success_rates": True,
        "alert_thresholds": {
            "response_time_seconds": 10,
            "success_rate_minimum": 0.90
        }
    }
}
```

## 📊 Architecture Benefits

### Scalability Advantages

**Horizontal Scaling**
```python
scalability_benefits = {
    "agent_independence": "Scale individual agents based on demand",
    "load_distribution": "Distribute queries across specialized agents",
    "fault_isolation": "Agent failures don't cascade system-wide",
    "resource_optimization": "Allocate resources per domain complexity"
}
```

**Maintenance Benefits**
```python
maintenance_advantages = {
    "modular_updates": "Update individual agents without system downtime",
    "specialized_debugging": "Isolate issues to specific domains",
    "incremental_improvements": "Enhance agents independently",
    "domain_expertise": "Deep optimization per business area"
}
```

### Performance Optimization

**Query Optimization**
- **Reduced Token Usage**: Smaller, focused prompts per agent
- **Faster Response Times**: Specialized agents process queries more efficiently  
- **Higher Success Rates**: Domain expertise reduces hallucinations
- **Parallel Processing**: Multiple agents work simultaneously

**Cost Optimization**
- **Efficient Token Utilization**: Optimized prompts reduce API costs
- **Caching Strategies**: Avoid redundant agent calls
- **Load Balancing**: Route queries to most efficient agents
- **Performance Monitoring**: Continuous optimization based on metrics

## 🎯 Best Practices

### Agent Design Principles

```python
agent_design_principles = {
    "single_responsibility": "Each agent owns one business domain",
    "clear_boundaries": "Well-defined data scope and expertise",
    "minimal_overlap": "Avoid duplicate functionality across agents", 
    "maximum_cohesion": "Related functionality grouped together",
    "loose_coupling": "Agents operate independently",
    "high_specialization": "Deep domain knowledge per agent"
}
```

### Query Optimization Strategies

```python
query_optimization = {
    "specific_agents": "Route to specialist instead of coordinator when possible",
    "parallel_execution": "Use coordinator for multi-domain queries",
    "context_preservation": "Maintain conversation context across agents",
    "error_recovery": "Graceful fallback between agents",
    "performance_monitoring": "Track and optimize based on metrics"
}
```

### Troubleshooting Multi-Agent Systems

```python
troubleshooting_guide = {
    "agent_not_found": "Verify agent creation with SHOW AGENTS;",
    "slow_response": "Check individual agent performance metrics",
    "incorrect_routing": "Review query classification logic",
    "correlation_errors": "Validate cross-database key relationships",
    "token_overflow": "Optimize prompt templates for agents"
}
```

## 📈 Success Metrics

### Multi-Agent Performance KPIs

```python
success_metrics = {
    "response_accuracy": "95%+ correct business insights",
    "query_routing": "90%+ optimal agent selection", 
    "cross_correlation": "Successful CNPJ-based data matching",
    "response_time": "<5 seconds for complex multi-agent queries",
    "cost_efficiency": "40% reduction vs single-agent approach",
    "system_reliability": "99.5% uptime with graceful degradation"
}
```

### Business Value Metrics

```python
business_value = {
    "compliance_automation": "Brazilian tax compliance reporting",
    "operational_intelligence": "Real-time business insights",
    "strategic_analytics": "Cross-functional business intelligence",
    "self_service_capability": "Business users query complex data independently",
    "regulatory_efficiency": "Automated fiscal analysis and reporting"
}
```

---

**🤖 Multi-Agent Architecture** - Advanced coordination system delivering specialized AI expertise with enterprise scalability, fault tolerance, and comprehensive business intelligence capabilities for Brazilian restaurant operations.