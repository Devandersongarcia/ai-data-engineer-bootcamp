# 🏛️ Relatórios de Compliance Fiscal - UberEats Brasil

## Query Melhorada para Compliance Fiscal

### 📋 **Relatório Completo de Compliance por Região**

```sql
-- Relatório de Compliance Fiscal Completo
SELECT 
    r.city AS cidade,
    r.cnpj AS cnpj_restaurante,
    r.name AS nome_restaurante,
    -- Total de notas fiscais
    COUNT(DISTINCT i.invoice_id) AS total_notas_fiscais,
    
    -- Status das notas fiscais
    SUM(CASE WHEN i.invoice_status = 'issued' THEN 1 ELSE 0 END) AS notas_emitidas,
    SUM(CASE WHEN i.invoice_status = 'paid' THEN 1 ELSE 0 END) AS notas_pagas,
    SUM(CASE WHEN i.invoice_status NOT IN ('issued', 'paid') THEN 1 ELSE 0 END) AS notas_problematicas,
    
    -- Validação de CNPJ (formato brasileiro: XX.XXX.XXX/XXXX-XX)
    CASE 
        WHEN r.cnpj ~ '^[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}$' THEN 'VÁLIDO'
        ELSE 'INVÁLIDO'
    END AS cnpj_status,
    
    -- Métricas fiscais
    SUM(i.tax_amount) AS total_impostos,
    AVG(i.tax_amount) AS imposto_medio,
    SUM(i.total_amount) AS faturamento_total,
    
    -- Taxa de compliance (% de notas válidas)
    ROUND(
        (SUM(CASE WHEN i.invoice_status IN ('issued', 'paid') THEN 1.0 ELSE 0 END) / 
         COUNT(DISTINCT i.invoice_id)) * 100, 2
    ) AS percentual_compliance,
    
    -- Últimas movimentações
    MAX(i.issue_date) AS ultima_nota_emitida,
    MIN(i.issue_date) AS primeira_nota_emitida

FROM ubereats_catalog.restaurants r
LEFT JOIN postgres_ubereats.orders o ON r.cnpj = o.restaurant_key
LEFT JOIN postgres_ubereats.invoices i ON o.order_id = i.order_key
WHERE r.cnpj IS NOT NULL
  AND i.issue_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY r.city, r.cnpj, r.name
HAVING COUNT(DISTINCT i.invoice_id) > 0
ORDER BY percentual_compliance DESC, total_impostos DESC
LIMIT 25;
```

### 🔍 **Análise de CNPJs Problemáticos**

```sql
-- Restaurantes com CNPJs inválidos ou problemas fiscais
SELECT 
    r.city AS cidade,
    r.cnpj AS cnpj_restaurante,
    r.name AS nome_restaurante,
    CASE 
        WHEN r.cnpj IS NULL THEN 'CNPJ AUSENTE'
        WHEN r.cnpj ~ '^[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}$' THEN 'CNPJ VÁLIDO'
        ELSE 'FORMATO INVÁLIDO'
    END AS status_cnpj,
    COUNT(DISTINCT i.invoice_id) AS total_notas,
    SUM(CASE WHEN i.invoice_status NOT IN ('issued', 'paid') THEN 1 ELSE 0 END) AS notas_problema,
    SUM(i.total_amount) AS faturamento_total
FROM ubereats_catalog.restaurants r
LEFT JOIN postgres_ubereats.orders o ON r.cnpj = o.restaurant_key
LEFT JOIN postgres_ubereats.invoices i ON o.order_id = i.order_key
WHERE (r.cnpj IS NULL 
    OR r.cnpj !~ '^[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}$'
    OR i.invoice_status NOT IN ('issued', 'paid'))
  AND i.issue_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY r.city, r.cnpj, r.name
ORDER BY faturamento_total DESC
LIMIT 20;
```

### 📊 **Dashboard de Compliance por Estado (Simulado)**

```sql
-- Agrupamento por "estado" usando as primeiras letras das cidades
SELECT 
    SUBSTRING(r.city, 1, 2) AS estado_simulado,
    COUNT(DISTINCT r.cnpj) AS total_restaurantes,
    
    -- CNPJs válidos
    SUM(CASE WHEN r.cnpj ~ '^[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}$' THEN 1 ELSE 0 END) AS cnpjs_validos,
    
    -- Status das notas
    COUNT(DISTINCT i.invoice_id) AS total_notas_fiscais,
    SUM(CASE WHEN i.invoice_status = 'paid' THEN 1 ELSE 0 END) AS notas_pagas,
    SUM(CASE WHEN i.invoice_status = 'issued' THEN 1 ELSE 0 END) AS notas_emitidas,
    
    -- Métricas fiscais consolidadas
    SUM(i.tax_amount) AS impostos_recolhidos,
    SUM(i.total_amount) AS receita_bruta_total,
    
    -- Taxa de compliance regional
    ROUND(
        (SUM(CASE WHEN i.invoice_status IN ('issued', 'paid') THEN 1.0 ELSE 0 END) / 
         COUNT(DISTINCT i.invoice_id)) * 100, 2
    ) AS taxa_compliance_regional

FROM ubereats_catalog.restaurants r
LEFT JOIN postgres_ubereats.orders o ON r.cnpj = o.restaurant_key
LEFT JOIN postgres_ubereats.invoices i ON o.order_id = i.order_key
WHERE r.cnpj IS NOT NULL
  AND i.issue_date >= CURRENT_DATE - INTERVAL '60 days'
GROUP BY SUBSTRING(r.city, 1, 2)
HAVING COUNT(DISTINCT r.cnpj) >= 3
ORDER BY taxa_compliance_regional DESC, impostos_recolhidos DESC
LIMIT 15;
```

### 🚨 **Alertas de Compliance**

```sql
-- Restaurantes que precisam de atenção fiscal
SELECT 
    r.name AS restaurante,
    r.city AS cidade,
    r.cnpj,
    COUNT(DISTINCT i.invoice_id) AS total_notas,
    
    -- Problemas identificados
    CASE 
        WHEN r.cnpj IS NULL THEN 'CNPJ AUSENTE'
        WHEN r.cnpj !~ '^[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}$' THEN 'CNPJ FORMATO INVÁLIDO'
        WHEN SUM(CASE WHEN i.invoice_status NOT IN ('issued', 'paid') THEN 1 ELSE 0 END) > 0 THEN 'NOTAS FISCAIS PROBLEMÁTICAS'
        WHEN AVG(i.tax_amount / i.total_amount) < 0.05 THEN 'CARGA TRIBUTÁRIA MUITO BAIXA'
        ELSE 'OK'
    END AS alerta_compliance,
    
    SUM(i.tax_amount) AS impostos_pagos,
    AVG(i.tax_amount / i.total_amount) AS taxa_tributaria_media,
    MAX(i.issue_date) AS ultima_nota

FROM ubereats_catalog.restaurants r
LEFT JOIN postgres_ubereats.orders o ON r.cnpj = o.restaurant_key  
LEFT JOIN postgres_ubereats.invoices i ON o.order_id = i.order_key
WHERE i.issue_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY r.name, r.city, r.cnpj
HAVING COUNT(DISTINCT i.invoice_id) > 5
   AND (r.cnpj IS NULL 
        OR r.cnpj !~ '^[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}$'
        OR SUM(CASE WHEN i.invoice_status NOT IN ('issued', 'paid') THEN 1 ELSE 0 END) > 0
        OR AVG(i.tax_amount / i.total_amount) < 0.05)
ORDER BY total_notas DESC
LIMIT 20;
```

## 💡 **Interpretação dos Resultados**

### ✅ **Indicadores de Boa Compliance:**
- CNPJs no formato correto (XX.XXX.XXX/XXXX-XX)
- Taxa de compliance > 95%
- Notas fiscais predominantemente 'issued' ou 'paid'
- Carga tributária entre 5-15% do faturamento

### 🚨 **Sinais de Alerta:**
- CNPJs ausentes ou formato incorreto
- Muitas notas com status diferente de 'issued'/'paid'
- Carga tributária < 5% (possível sonegação)
- Ausência de notas fiscais por períodos longos

### 📋 **Ações Recomendadas:**
1. **CNPJs Inválidos**: Solicitar correção cadastral
2. **Notas Problemáticas**: Investigar status e regularizar
3. **Baixa Carga Tributária**: Auditoria fiscal detalhada
4. **Falta de Movimentação**: Verificar atividade do restaurante

---

**🎯 Use estas queries para análises mais precisas de compliance fiscal!**