# Langfuse Integration Guide - Advanced Prompt Management & Observability

Complete setup and usage guide for Langfuse integration in the UberEats Brasil development environment.

## 🎯 What is Langfuse?

Langfuse is an open-source LLM engineering platform that provides:
- **Centralized Prompt Management**: Version control for AI prompts
- **Advanced Observability**: Token usage, cost tracking, performance monitoring
- **A/B Testing**: Compare prompt versions and optimize performance
- **Team Collaboration**: Non-technical team members can update prompts
- **Analytics Dashboard**: Comprehensive usage and performance insights

## 🚀 Quick Setup (5 minutes)

### 1. Create Langfuse Account
```bash
# Visit and create account
open https://cloud.langfuse.com

# Choose your region
# US: https://us.cloud.langfuse.com
# EU: https://cloud.langfuse.com
```

### 2. Get API Keys
1. Create a new project: "UberEats Brasil Development"
2. Navigate to **Settings** → **API Keys**
3. Generate new keys:
   - **Secret Key**: `sk-lf-...` (server-side operations)
   - **Public Key**: `pk-lf-...` (client-side operations)

### 3. Configure Environment
```bash
cd src/development

# Add to your .env file
cat >> .env << EOF

# Langfuse Configuration
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_ENABLED=true
LANGFUSE_TRACING_ENABLED=true
LANGFUSE_SAMPLE_RATE=1.0
EOF
```

### 4. Initialize Prompts
```bash
# Migrate your prompts to Langfuse
python utils/migrate_prompts.py

# Expected output:
# ✅ Created prompt: sql_system_message
# ✅ Created prompt: sql_generation_template  
# ✅ Migration completed successfully
```

### 5. Test Integration
```bash
# Verify everything works
python utils/test_langfuse_integration.py

# Expected output:
# ✅ Langfuse connection successful
# ✅ Prompt fetching works
# ✅ Tracing is functional
# ✅ All systems operational
```

## 📋 Prompt Management

### Understanding the Prompt System

**Two Core Prompts Created**
```
1. sql_system_message (System Prompt)
   - Defines the AI assistant's role and capabilities
   - Sets context for Brazilian tax compliance
   - Establishes safety and validation rules

2. sql_generation_template (Template Prompt)
   - Main business logic for SQL generation
   - Database schema information
   - Query examples and patterns
   - Output formatting rules
```

### Prompt Structure in Langfuse

**System Message Example**
```
Name: sql_system_message
Type: System
Content: You are an expert SQL assistant specialized in Brazilian fiscal compliance...
Labels: [production, development]
Config: {"model": "gpt-3.5-turbo", "temperature": 0}
```

**Template Prompt Example**
```
Name: sql_generation_template  
Type: Template
Content: Generate SQL for UberEats Brasil data...
Variables: [schema_info, user_question, business_rules]
Labels: [production, development]
```

### Dynamic Prompt Updates

**Real-time Changes**
```python
# In Langfuse Dashboard:
# 1. Edit prompt content
# 2. Save changes
# 3. Changes take effect immediately - no deployment needed!

# Your application automatically uses updated prompts
prompt = langfuse.get_prompt(
    name="sql_generation_template",
    label="production"  # Always gets latest version
)
```

**Version Control**
```python
# Langfuse automatically versions all changes
prompt_v1 = langfuse.get_prompt("sql_system_message", version=1)
prompt_v2 = langfuse.get_prompt("sql_system_message", version=2)

# Compare performance between versions
performance_v1 = analyze_prompt_performance(prompt_v1)  
performance_v2 = analyze_prompt_performance(prompt_v2)
```

## 📊 Advanced Observability

### Real-time Tracing

**Every Query Traced**
```python
# Automatic tracing for every request
trace_data = {
    "session_id": "a7bb1b8b-6e36-4077-8e53-d57b27ec977c",
    "user_question": "Top 5 restaurantes por faturamento",
    "generated_sql": "SELECT r.name, SUM(i.total_amount)...",
    "execution_time": 2.1,
    "tokens_used": {
        "input": 150,
        "output": 25, 
        "total": 175
    },
    "cost": 0.000275,
    "success": True
}
```

**Performance Breakdown**
```
Request Timeline:
├── 🔄 Prompt Loading (50ms)
├── 🤖 SQL Generation (1,800ms)  
├── ✅ Query Validation (20ms)
├── 🗄️ Database Execution (430ms)
└── 📊 Result Formatting (100ms)
Total: 2,400ms
```

### Cost Tracking

**Automatic Cost Calculation**
```python
# Real-time cost tracking
cost_breakdown = {
    "model": "gpt-3.5-turbo",
    "input_tokens": 150,
    "input_cost": 150 * 0.0015 / 1000,  # $0.000225
    "output_tokens": 25,
    "output_cost": 25 * 0.002 / 1000,   # $0.000050
    "total_cost": 0.000275
}

# Budget monitoring
daily_spending = sum_costs_today()  # $2.45
monthly_budget = 100.00  # $100
utilization = daily_spending / (monthly_budget / 30)  # 81.7%
```

**Cost Optimization Insights**
```python
# Langfuse Analytics Dashboard shows:
expensive_queries = [
    {"query": "Complex fiscal analysis", "avg_cost": "$0.0045"},
    {"query": "Multi-table joins", "avg_cost": "$0.0038"},
    {"query": "Regional breakdowns", "avg_cost": "$0.0032"}
]

# Optimization opportunities
optimizations = {
    "prompt_efficiency": "Reduce template length by 15%",
    "caching": "Cache repeated schema info",
    "model_selection": "Use gpt-3.5 for simple queries"
}
```

### User Analytics

**Session Tracking**
```python
# Complete conversation flows tracked
session_analytics = {
    "session_id": "user_123_20250826", 
    "queries": 8,
    "success_rate": 87.5,
    "avg_response_time": 2.1,
    "total_cost": 0.0023,
    "query_types": {
        "revenue_analysis": 3,
        "compliance_checks": 2, 
        "regional_reports": 3
    }
}
```

**Usage Patterns**
```python
# Identify trends and optimize
usage_insights = {
    "peak_hours": [9, 14, 16],  # 9am, 2pm, 4pm
    "common_questions": [
        "Top restaurantes por faturamento",
        "Análise fiscal por estado", 
        "Status das notas fiscais"
    ],
    "user_segments": {
        "power_users": 3,      # >20 queries/day
        "regular_users": 12,   # 5-20 queries/day  
        "occasional_users": 25  # <5 queries/day
    }
}
```

## 🎨 Dashboard Features

### Langfuse Dashboard Navigation

**Main Sections**
```
📊 Overview
├── Request volume and trends
├── Success rate monitoring  
├── Cost tracking and budgets
└── Performance metrics

🔍 Traces  
├── Individual request details
├── Performance breakdown
├── Error analysis and debugging
└── Token usage per request

📝 Prompts
├── Prompt management interface
├── Version history and rollbacks
├── A/B testing configuration  
└── Performance comparisons

👥 Users
├── User behavior analysis
├── Usage segmentation
└── Session analytics

📈 Analytics
├── Custom dashboards
├── Usage trends over time
├── Cost analysis and optimization
└── Performance optimization insights
```

### Custom Dashboards

**Business Intelligence Views**
```python
# Create custom views in Langfuse
fiscal_compliance_dashboard = {
    "name": "Brazilian Fiscal Compliance",
    "metrics": [
        "queries_by_tax_type",
        "compliance_check_success_rate",
        "cnpj_validation_accuracy",
        "regional_analysis_usage"
    ],
    "time_range": "last_30_days",
    "filters": {
        "user_type": "fiscal_analyst",
        "query_category": "compliance"
    }
}
```

**Performance Monitoring**
```python
# System health dashboard
performance_dashboard = {
    "response_times": {
        "p50": 1.8,  # 50th percentile
        "p95": 3.2,  # 95th percentile  
        "p99": 5.1   # 99th percentile
    },
    "success_rates": {
        "sql_generation": 94.2,
        "query_execution": 98.7,
        "overall": 92.9
    },
    "cost_trends": {
        "daily_average": "$2.45",
        "weekly_total": "$17.15",
        "monthly_projection": "$73.50"
    }
}
```

## 🧪 A/B Testing

### Prompt Optimization

**Setting Up Tests**
```python
# Create prompt variations in Langfuse
prompt_a = create_prompt(
    name="sql_generation_template",
    content="Version A: Detailed business context...",
    label="experiment_a"
)

prompt_b = create_prompt(
    name="sql_generation_template", 
    content="Version B: Concise technical approach...",
    label="experiment_b"
)

# Route traffic between versions
def get_prompt_for_user(user_id):
    if hash(user_id) % 2 == 0:
        return langfuse.get_prompt("sql_generation_template", "experiment_a")
    else:
        return langfuse.get_prompt("sql_generation_template", "experiment_b")
```

**Performance Comparison**
```python
# Automatic A/B test analysis
test_results = {
    "experiment_a": {
        "success_rate": 89.3,
        "avg_response_time": 2.4,
        "cost_per_query": 0.00032,
        "user_satisfaction": 4.2
    },
    "experiment_b": {
        "success_rate": 94.1,  # Winner!
        "avg_response_time": 1.9,  # Winner!
        "cost_per_query": 0.00028,  # Winner!
        "user_satisfaction": 4.6  # Winner!
    },
    "recommendation": "Deploy experiment_b to production"
}
```

### Business Impact Testing

**Fiscal Compliance Optimization**
```python
# Test different approaches to tax calculations
tax_prompt_variants = {
    "detailed": "Include comprehensive tax calculation examples...",
    "simplified": "Focus on core tax rules only...", 
    "regional": "Emphasize state-specific tax variations..."
}

# Measure business impact
business_metrics = {
    "detailed": {"accuracy": 96%, "compliance": 94%},
    "simplified": {"accuracy": 91%, "compliance": 89%},
    "regional": {"accuracy": 98%, "compliance": 97%}  # Winner!
}
```

## 🔧 Advanced Configuration

### Environment Controls

**Feature Toggles**
```bash
# Complete control over Langfuse features
LANGFUSE_ENABLED=true              # Master switch
LANGFUSE_TRACING_ENABLED=true      # Observability
LANGFUSE_SAMPLE_RATE=1.0           # Trace 100% of requests
LANGFUSE_DEBUG_MODE=false          # Debug logging
LANGFUSE_BATCH_SIZE=10             # Batch uploads
LANGFUSE_FLUSH_INTERVAL=5000       # Flush every 5s
```

**Performance Tuning**
```python
# Optimize for your usage patterns
langfuse_config = {
    "max_retries": 3,
    "timeout": 10,
    "batch_size": 10,
    "flush_interval": 5000,
    "enable_local_cache": True,
    "cache_ttl": 300  # 5 minutes
}
```

### Security & Privacy

**Data Controls**
```python
# Control what data is sent to Langfuse
privacy_settings = {
    "include_user_inputs": True,     # Natural language questions
    "include_sql_outputs": True,     # Generated SQL
    "include_query_results": False,  # Don't send actual data
    "include_user_ids": True,        # Anonymous user tracking
    "include_ip_addresses": False,   # Privacy protection
    "data_retention_days": 90        # Auto-delete after 90 days
}
```

**Compliance Features**
```python
# Brazilian LGPD compliance
gdpr_settings = {
    "anonymize_users": True,
    "exclude_pii": True,
    "retention_policy": "90_days",
    "deletion_on_request": True,
    "audit_logging": True
}
```

## 🚨 Troubleshooting

### Common Issues

**"Langfuse service not available"**
```bash
# Check API keys
echo $LANGFUSE_SECRET_KEY
echo $LANGFUSE_PUBLIC_KEY

# Test connectivity  
curl -X GET "$LANGFUSE_HOST/api/public/health"

# Verify credentials in dashboard
python -c "
from langfuse import Langfuse
lf = Langfuse()
print('✅ Connection successful')
"
```

**"Prompt not found"**
```bash
# Check if prompts exist
python -c "
from core.langfuse_service import LangfuseService
from config.settings import get_dev_settings
lf = LangfuseService(get_dev_settings())
prompts = lf.client.get_prompts()
print([p.name for p in prompts])
"

# Re-run migration if needed
python utils/migrate_prompts.py
```

**"Tracing not working"**
```bash
# Enable debug logging
export LANGFUSE_DEBUG_MODE=true
export LOG_LEVEL=DEBUG

# Check trace uploads
python utils/test_tracing.py

# Verify dashboard shows traces
open https://cloud.langfuse.com/traces
```

### Performance Issues

**Slow Response Times**
```python
# Check if Langfuse is causing delays
import time

# Measure with/without Langfuse
start = time.time()
result_with_langfuse = process_query("test query")
time_with = time.time() - start

# Disable temporarily
os.environ["LANGFUSE_ENABLED"] = "false"
start = time.time() 
result_without = process_query("test query")
time_without = time.time() - start

langfuse_overhead = time_with - time_without
print(f"Langfuse overhead: {langfuse_overhead:.3f}s")
```

**High Costs**
```python
# Analyze cost drivers
cost_analysis = {
    "expensive_prompts": identify_costly_prompts(),
    "token_optimization": suggest_optimizations(),
    "caching_opportunities": find_duplicate_queries(),
    "model_efficiency": compare_model_costs()
}

# Implement optimizations
optimize_prompts(cost_analysis["expensive_prompts"])
enable_caching(cost_analysis["caching_opportunities"])
```

### Debug Mode

**Comprehensive Diagnostics**
```bash
# Run full diagnostic suite
python utils/test_langfuse_integration.py --verbose

# Check all system components
python -c "
from core.langfuse_service import LangfuseService
from config.settings import get_dev_settings

settings = get_dev_settings()
service = LangfuseService(settings)

# Test each component
print('Config:', service.health_check())
print('Prompts:', service.test_prompt_access())  
print('Tracing:', service.test_tracing())
print('Analytics:', service.test_analytics_access())
"
```

## 📈 Best Practices

### Prompt Management

**Versioning Strategy**
```python
# Use semantic versioning for prompts
prompt_versions = {
    "v1.0.0": "Initial release",
    "v1.1.0": "Added Brazilian tax context", 
    "v1.2.0": "Improved query optimization",
    "v2.0.0": "Complete rewrite with better examples"
}

# Use labels for environments
labels = {
    "production": "Stable, battle-tested prompts",
    "staging": "Pre-production testing", 
    "development": "Active development",
    "experimental": "Research and experiments"
}
```

**Content Guidelines**
```python
# Effective prompt structure
prompt_template = """
## Role Definition
You are an expert SQL analyst for UberEats Brasil...

## Context & Data
Database schema: {schema_info}
Business rules: {business_rules}

## Task
Generate SQL for: {user_question}

## Constraints  
- Only SELECT operations allowed
- Must include LIMIT clause
- Follow Brazilian tax compliance rules
- Return valid PostgreSQL syntax

## Examples
Input: "Top 5 restaurants by revenue"
Output: SELECT r.name, SUM(i.total_amount)...
"""
```

### Cost Optimization

**Token Efficiency**
```python
# Optimize prompt length
def optimize_prompt(original_prompt):
    # Remove redundant examples
    concise_examples = select_best_examples(original_prompt.examples)
    
    # Compress schema information
    essential_schema = extract_key_schema_info(schema)
    
    # Maintain effectiveness while reducing tokens
    optimized = create_prompt(concise_examples, essential_schema)
    
    return optimized

# A/B test optimizations
test_optimization(original_prompt, optimized_prompt)
```

**Smart Caching**
```python
# Cache expensive operations
@cache_with_ttl(300)  # 5 minutes
def get_schema_info():
    return expensive_schema_lookup()

@cache_prompt_responses(1800)  # 30 minutes  
def process_similar_queries(question_hash):
    return generate_sql_if_not_cached(question_hash)
```

### Monitoring Strategy

**Key Metrics to Track**
```python
critical_metrics = {
    "success_rate": {
        "target": ">95%",
        "alert_threshold": "<90%"
    },
    "response_time": {
        "target": "<2s average",  
        "alert_threshold": ">5s"
    },
    "cost_per_query": {
        "target": "<$0.001",
        "alert_threshold": ">$0.005"  
    },
    "user_satisfaction": {
        "target": ">4.0/5.0",
        "measurement": "implicit feedback"
    }
}
```

**Alerting Setup**
```python
# Configure alerts in Langfuse
alerts = {
    "high_error_rate": {
        "condition": "error_rate > 10% over 15 minutes",
        "notification": "slack://dev-alerts"
    },
    "cost_spike": {
        "condition": "daily_cost > $10",
        "notification": "email://admin@company.com"
    },
    "performance_degradation": {
        "condition": "avg_response_time > 5s over 30 minutes", 
        "notification": "pagerduty://on-call"
    }
}
```

---

## 🎯 Success Metrics

After implementing Langfuse, you should see:

**Operational Improvements**
- ✅ **Zero-downtime prompt updates**
- ✅ **50% reduction in debugging time**
- ✅ **Complete cost visibility**
- ✅ **Improved query success rates**

**Business Impact**  
- ✅ **Faster prompt iteration cycles**
- ✅ **Data-driven optimization decisions**
- ✅ **Better user experience through A/B testing**
- ✅ **Reduced operational costs**

**Team Collaboration**
- ✅ **Non-technical team members can update prompts**
- ✅ **Shared visibility into system performance**
- ✅ **Historical data for decision making**
- ✅ **Automated performance monitoring**

---

**🚀 Ready to get started?** Run `python utils/migrate_prompts.py` and unlock the full power of advanced prompt management and observability!