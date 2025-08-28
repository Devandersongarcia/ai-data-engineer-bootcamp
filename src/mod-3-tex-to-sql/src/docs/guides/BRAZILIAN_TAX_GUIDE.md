# Brazilian Tax Compliance Guide

**Comprehensive guide to Brazilian tax compliance automation across all UberEats Brasil environments.**

## 🇧🇷 Overview

All three environments (Development, Production, MindsDB) include specialized support for Brazilian tax compliance, focusing on restaurant and food delivery operations with automated ICMS, ISS, and PIS/COFINS calculations.

## 📊 Brazilian Tax System Overview

### Primary Tax Types

#### ICMS (Imposto sobre Circulação de Mercadorias e Serviços)
**State Tax on Goods and Services**
- **Rate**: 17-18% (varies by state)
- **Applies to**: Product sales, delivery services
- **Calculation**: Based on invoice value
- **Compliance**: Monthly reporting required

#### ISS (Imposto sobre Serviços)
**Municipal Service Tax**
- **Rate**: 2-5% (varies by municipality)  
- **Applies to**: Service provision (delivery, preparation)
- **Calculation**: Based on service value
- **Compliance**: Monthly reporting to municipality

#### PIS/COFINS (Federal Taxes)
**Federal Taxes on Revenue**
- **PIS Rate**: 1.65% (standard) or 0.65% (simplified)
- **COFINS Rate**: 7.6% (standard) or 3% (simplified)
- **Applies to**: Total revenue
- **Regime**: Depends on company size and structure

### Tax Calculation Examples

#### Restaurant Invoice Analysis
```sql
-- ICMS calculation by state
SELECT 
    state,
    SUM(invoice_value) as total_sales,
    SUM(invoice_value * 0.18) as icms_owed,
    COUNT(*) as invoice_count
FROM ubears_invoices_extract_airflow 
WHERE invoice_date >= '2024-01-01'
GROUP BY state
ORDER BY total_sales DESC;
```

#### Service Tax Analysis  
```sql
-- ISS calculation by municipality
SELECT 
    city,
    SUM(service_value) as total_services,
    SUM(service_value * 0.05) as iss_owed,
    AVG(service_value * 0.05) as avg_iss_per_invoice
FROM service_invoices
WHERE service_type IN ('delivery', 'food_preparation')
GROUP BY city;
```

## 🚀 Environment-Specific Tax Features

### Development Environment Tax Features

#### Advanced Tax Query Examples
```python
# Natural language tax queries
queries = [
    "Análise de ICMS por estado nos últimos 3 meses",
    "Total de ISS recolhido por cidade em 2024", 
    "Compliance fiscal dos restaurantes de São Paulo",
    "Quebra de impostos PIS/COFINS por tipo de negócio"
]

for query in queries:
    result = converter.process_question(query)
    print(f"Query: {query}")
    print(f"SQL: {result['sql_query']}")
    print(f"Results: {len(result['result'])} records")
```

#### Tax Compliance Validation
```python
def validate_tax_compliance(restaurant_cnpj):
    """Validate tax compliance for specific restaurant"""
    
    # Check ICMS compliance
    icms_query = f"""
    SELECT 
        SUM(total_amount * 0.18) as icms_owed,
        COUNT(*) as invoice_count,
        MIN(invoice_date) as period_start,
        MAX(invoice_date) as period_end
    FROM ubears_invoices_extract_airflow 
    WHERE restaurant_cnpj = '{restaurant_cnpj}'
    AND invoice_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
    """
    
    # Check ISS compliance  
    iss_query = f"""
    SELECT 
        city,
        SUM(service_amount * 0.05) as iss_owed,
        tax_status
    FROM service_records
    WHERE restaurant_cnpj = '{restaurant_cnpj}'
    """
    
    return {
        "icms": execute_sql(icms_query),
        "iss": execute_sql(iss_query),
        "compliance_status": "compliant" if all_taxes_paid else "pending"
    }
```

### Production Environment Tax Features

#### High-Performance Tax Calculations
```python
from core.enhanced_vanna_converter import EnhancedVannaTextToSQLConverter

# Optimized for tax compliance queries
tax_converter = EnhancedVannaTextToSQLConverter(
    primary_table="ubears_invoices_extract_airflow"
)

# Cached tax calculations for performance
tax_queries = [
    "ICMS por estado último mês",
    "ISS por cidade último trimestre", 
    "PIS/COFINS breakdown por categoria"
]

for query in tax_queries:
    result = tax_converter.process_question(query)
    # Results cached for 30 minutes for repeat analysis
```

#### Brazilian Tax Patterns (Built-in)
```python
# Pre-configured tax calculation patterns
tax_patterns = {
    "icms_por_estado": """
        SELECT 
            COALESCE(restaurant_state, 'N/A') as estado,
            COUNT(*) as total_invoices,
            SUM(total_amount) as revenue,
            ROUND(SUM(total_amount * 0.18), 2) as icms_owed,
            ROUND(AVG(total_amount), 2) as avg_invoice_value
        FROM ubears_invoices_extract_airflow 
        WHERE invoice_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
        GROUP BY restaurant_state 
        ORDER BY revenue DESC
    """,
    
    "iss_por_cidade": """
        SELECT 
            COALESCE(restaurant_city, 'N/A') as cidade,
            COUNT(*) as invoices,
            SUM(service_amount) as service_total,
            ROUND(SUM(service_amount * 0.05), 2) as iss_owed
        FROM service_invoices
        WHERE service_date >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY restaurant_city
        ORDER BY service_total DESC
    """
}
```

### MindsDB Environment Tax Features  

#### Specialized Tax Compliance Agent
```python
# PostgreSQL agent optimized for tax compliance
from core.mindsdb_client import connect

server = connect()
tax_agent = server.agents.get("agent_postgres_transactions")

# Complex tax compliance analysis
tax_response = tax_agent.completion([{
    "role": "user",
    "content": """
    Análise completa de compliance fiscal para restaurantes:
    1. ICMS por estado nos últimos 6 meses
    2. ISS por município com inadimplências 
    3. PIS/COFINS breakdown por categoria de restaurante
    4. Relatório de conformidade fiscal geral
    """
}])
```

#### Multi-Agent Tax Workflow
```python
# Coordinator orchestrating tax compliance across databases
coordinator = server.agents.get("agent_ubereats_coordinator")

complex_tax_analysis = coordinator.completion([{
    "role": "user", 
    "content": """
    Preciso de uma análise fiscal integrada:
    
    1. PostgreSQL: Dados fiscais e de pagamentos
    2. MongoDB: Informações dos restaurantes (categoria, localização)  
    3. Correlação: Compliance por tipo de restaurante
    4. Recomendações: Otimização fiscal por região
    """
}])

# Coordinator will:
# 1. Query PostgreSQL agent for tax data
# 2. Query MongoDB agent for restaurant categories
# 3. Correlate data by restaurant CNPJ
# 4. Generate comprehensive tax compliance report
```

## 📊 Tax Compliance Reports

### Monthly ICMS Report
```sql
-- ICMS collection by state (monthly)
SELECT 
    restaurant_state as estado,
    EXTRACT(MONTH FROM invoice_date) as mes,
    EXTRACT(YEAR FROM invoice_date) as ano,
    COUNT(*) as total_notas,
    SUM(total_amount) as faturamento_bruto,
    ROUND(SUM(total_amount * 0.18), 2) as icms_devido,
    ROUND(SUM(CASE 
        WHEN tax_status = 'paid' THEN total_amount * 0.18 
        ELSE 0 
    END), 2) as icms_recolhido,
    ROUND(SUM(CASE 
        WHEN tax_status != 'paid' THEN total_amount * 0.18 
        ELSE 0 
    END), 2) as icms_pendente
FROM ubears_invoices_extract_airflow
WHERE invoice_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '6 months')
GROUP BY restaurant_state, EXTRACT(MONTH FROM invoice_date), EXTRACT(YEAR FROM invoice_date)
ORDER BY ano DESC, mes DESC, faturamento_bruto DESC;
```

### ISS Compliance Dashboard
```sql  
-- ISS compliance by municipality
SELECT 
    restaurant_city as municipio,
    COUNT(DISTINCT restaurant_cnpj) as restaurantes_ativos,
    SUM(service_amount) as total_servicos,
    ROUND(SUM(service_amount * 0.05), 2) as iss_devido,
    COUNT(CASE WHEN iss_status = 'compliant' THEN 1 END) as restaurantes_em_dia,
    COUNT(CASE WHEN iss_status = 'pending' THEN 1 END) as restaurantes_pendentes,
    ROUND(
        COUNT(CASE WHEN iss_status = 'compliant' THEN 1 END) * 100.0 / 
        COUNT(DISTINCT restaurant_cnpj), 2
    ) as percentual_compliance
FROM service_invoices s
JOIN restaurants r ON s.restaurant_cnpj = r.cnpj
WHERE service_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY restaurant_city
ORDER BY total_servicos DESC;
```

### PIS/COFINS Analysis
```sql
-- Federal tax analysis by business category
SELECT 
    business_category as categoria,
    COUNT(DISTINCT restaurant_cnpj) as restaurantes,
    SUM(gross_revenue) as receita_bruta,
    ROUND(SUM(gross_revenue * 0.0165), 2) as pis_devido,
    ROUND(SUM(gross_revenue * 0.076), 2) as cofins_devido,
    ROUND(SUM(gross_revenue * (0.0165 + 0.076)), 2) as total_federal_taxes,
    ROUND(SUM(gross_revenue * (0.0165 + 0.076)) / SUM(gross_revenue) * 100, 2) as aliquota_efetiva
FROM restaurant_revenue rv
JOIN restaurants r ON rv.restaurant_cnpj = r.cnpj
WHERE revenue_date >= DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '3 months')
GROUP BY business_category
ORDER BY receita_bruta DESC;
```

## 🎯 Tax Query Examples by Use Case

### Restaurant Owner Queries
```
"Quanto de ICMS meu restaurante deve recolher este mês?"
"Status de compliance fiscal do meu CNPJ"
"Comparação de impostos com restaurantes similares na região"
"Projeção de ISS para o próximo trimestre"
```

### Tax Accountant Queries  
```
"Relatório completo de ICMS por estado nos últimos 6 meses"
"Restaurantes com pendências fiscais em São Paulo"
"Breakdown de PIS/COFINS por categoria de negócio"
"Análise de compliance municipal por cidade"
```

### Government Auditor Queries
```
"Total de impostos recolhidos por região no último ano"
"Identificar padrões de inadimplência fiscal"
"Ranking de municípios por arrecadação de ISS"
"Análise de sonegação por tipo de estabelecimento"
```

### Business Analyst Queries
```
"Impacto fiscal na margem de lucro por região"
"Otimização tributária para novos restaurantes"
"Correlação entre carga tributária e performance"
"Benchmark fiscal por categoria de restaurante"
```

## 🛡️ Compliance Best Practices

### Data Validation
```python
def validate_tax_data():
    """Validate tax calculation data integrity"""
    
    validations = [
        {
            "name": "CNPJ Format Validation",
            "query": """
                SELECT COUNT(*) FROM restaurants 
                WHERE cnpj !~ '^[0-9]{2}\\.[0-9]{3}\\.[0-9]{3}/[0-9]{4}-[0-9]{2}$'
            """,
            "expected": 0
        },
        {
            "name": "Tax Rate Consistency", 
            "query": """
                SELECT DISTINCT tax_rate FROM invoices 
                WHERE tax_type = 'ICMS' AND tax_rate NOT BETWEEN 0.17 AND 0.18
            """,
            "expected": "empty_result"
        },
        {
            "name": "Missing Tax Information",
            "query": """
                SELECT COUNT(*) FROM ubears_invoices_extract_airflow
                WHERE tax_status IS NULL OR total_amount IS NULL
            """,
            "expected": 0
        }
    ]
    
    for validation in validations:
        result = execute_sql(validation["query"])
        if result != validation["expected"]:
            logger.warning(f"Tax validation failed: {validation['name']}")
```

### Audit Trail
```python
def create_tax_audit_log(query, result, user_id):
    """Create audit log for tax-related queries"""
    
    audit_log = {
        "timestamp": datetime.now(),
        "user_id": user_id,
        "query_type": "tax_compliance",
        "query": query,
        "result_count": len(result) if result else 0,
        "sensitive_data": True,
        "compliance_check": True
    }
    
    # Log to secure audit system
    audit_logger.info(json.dumps(audit_log))
```

## 📈 Tax Analytics Dashboards

### Executive Tax Dashboard
```
📊 Brazilian Tax Overview (Last 30 Days)
├── 💰 Total Revenue: R$ 2,847,392.50
├── 📋 ICMS Owed: R$ 512,530.65 (18%)
├── 🏛️ ISS Owed: R$ 142,369.63 (5%)  
├── 🇧🇷 PIS/COFINS: R$ 218,046.85 (7.65%)
└── 📈 Compliance Rate: 94.2%

🗺️ Top States by Revenue
├── São Paulo: R$ 1,238,294.20 (43.5%)
├── Rio de Janeiro: R$ 592,847.35 (20.8%)
├── Minas Gerais: R$ 387,392.18 (13.6%)
└── Others: R$ 628,858.77 (22.1%)

⚠️ Compliance Issues
├── 📍 12 restaurants with pending ICMS
├── 🏛️ 8 municipalities with ISS overdue  
└── 📊 5 restaurants missing tax documentation
```

### Regional Tax Performance
```
🌍 Regional Tax Analysis - Southeast Region
├── 📈 Growth Rate: +12.3% vs last quarter
├── 💸 Effective Tax Rate: 23.2% of revenue
├── 🏆 Best Performing City: Campinas (96.8% compliance)
└── ⚠️ Attention Needed: Santos (78.2% compliance)

📊 Tax Efficiency Ranking
1. 🥇 Fast Food: 21.1% effective rate
2. 🥈 Casual Dining: 23.4% effective rate  
3. 🥉 Fine Dining: 25.7% effective rate
4. 📈 Food Trucks: 19.8% effective rate
```

## 🔍 Advanced Tax Features

### Predictive Tax Analysis (MindsDB)
```python
# Use MindsDB ML models for tax prediction
tax_prediction_query = """
    SELECT 
        restaurant_cnpj,
        predicted_icms_next_month,
        confidence_score,
        risk_factors
    FROM mindsdb.tax_prediction_model
    WHERE restaurant_state = 'SP'
    AND revenue_trend = 'growing'
"""

# Agent query for predictive analysis
prediction_result = tax_agent.completion([{
    "role": "user",
    "content": f"Predição de impostos para próximo mês: {tax_prediction_query}"
}])
```

### Tax Optimization Recommendations
```python
def generate_tax_optimization_recommendations(restaurant_cnpj):
    """Generate tax optimization recommendations"""
    
    recommendations = []
    
    # Analyze current tax burden
    current_burden = calculate_tax_burden(restaurant_cnpj)
    
    # Regional comparisons
    regional_average = get_regional_tax_average(restaurant_cnpj)
    
    # Optimization opportunities
    if current_burden > regional_average * 1.1:
        recommendations.append({
            "type": "tax_planning",
            "message": "Carga tributária 10% acima da média regional",
            "action": "Revisar estrutura tributária e incentivos fiscais"
        })
    
    # Compliance improvements
    compliance_score = get_compliance_score(restaurant_cnpj)
    if compliance_score < 0.95:
        recommendations.append({
            "type": "compliance",
            "message": f"Score de compliance: {compliance_score:.1%}",
            "action": "Implementar sistema de gestão fiscal automatizado"
        })
    
    return recommendations
```

## 📞 Tax Compliance Support

### Getting Help
- **Tax Queries**: Use natural language - "ICMS por estado", "compliance fiscal"
- **Calculations**: Built-in Brazilian tax rates and formulas
- **Reports**: Pre-configured compliance dashboards
- **Validation**: Automated data integrity checks

### Emergency Tax Support
```bash
# Quick tax compliance check
python -c "
from utils.tax_compliance import quick_audit
result = quick_audit()
print(f'Compliance Status: {result[\"status\"]}')
print(f'Issues Found: {len(result[\"issues\"])}')
"
```

---

## 🇧🇷 Brazilian Tax Compliance Ready

**Comprehensive Tax Features**
- ✅ **ICMS Automation**: State tax calculations and reporting
- ✅ **ISS Management**: Municipal service tax compliance
- ✅ **PIS/COFINS Tracking**: Federal tax monitoring
- ✅ **Compliance Dashboard**: Real-time compliance monitoring

**Business Value**
- ✅ **Automated Compliance**: Reduce manual tax calculations
- ✅ **Risk Mitigation**: Identify compliance issues early
- ✅ **Cost Optimization**: Find tax efficiency opportunities  
- ✅ **Audit Readiness**: Complete audit trails and reporting

---

**🍔 UberEats Brasil Tax Compliance** - Comprehensive Brazilian tax automation with ICMS, ISS, and PIS/COFINS support across all environments.