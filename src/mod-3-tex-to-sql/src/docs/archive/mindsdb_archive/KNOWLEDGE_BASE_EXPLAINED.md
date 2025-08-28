# 🧠 Knowledge Bases in MindsDB - Complete Guide

## 🤔 **What is a Knowledge Base?**

A **Knowledge Base** in MindsDB is a collection of documents/files that agents can reference for additional context beyond their database tables.

---

## 📚 **Knowledge Base vs Agent Prompt**

### **Agent Prompt (What we're using):**
```sql
prompt_template = 'Expert fiscal brasileiro. ICMS: 17-18%, ISS: 2-5%...'
```
✅ **Embedded knowledge** directly in the agent
✅ **No extra setup** required
✅ **Works immediately**

### **Knowledge Base (Optional enhancement):**
```sql
CREATE KNOWLEDGE_BASE brasil_fiscal_kb
FROM (
  SELECT 'ICMS varies 17-18% by state' as content
  UNION ALL  
  SELECT 'ISS applies 2-5% on delivery services' as content
);
```
✅ **Separate document storage**
✅ **Can be updated independently**  
✅ **Better for large documents**

---

## 🎯 **Current Setup (No KB Needed)**

Your agents are **already complete** without knowledge bases because:

### **✅ Brazilian Tax Knowledge is Embedded:**
```sql
-- In the agent prompt template:
IMPOSTOS BRASILEIROS:
- ICMS: 17-18% mercadorias (varia estado)
- ISS: 2-5% servicos (taxa entrega)  
- PIS/COFINS: 3.65% federal
```

### **✅ Real Data Context is Included:**
```sql
-- Agent knows your actual data:
STATUS: issued(350), paid(125), cancelled(15), refunded(10)
CIDADES: Peixoto, Rios, Pimenta, da Mota Verde
```

---

## 🔧 **When to Use Knowledge Bases**

### **Use KB When:**
- 📄 **Large documents** (tax regulations, manuals)
- 🔄 **Frequently changing** content (policies, rates)
- 📚 **Multiple documents** per domain
- 🔗 **External references** (PDFs, websites)

### **Skip KB When:**
- ✅ **Simple context** fits in prompt (your case)
- ✅ **Static knowledge** that doesn't change
- ✅ **Small data** (few facts/rules)

---

## 📊 **Your Current Architecture (Perfect!)**

```sql
-- Agent with embedded knowledge (NO KB needed)
CREATE AGENT agent_postgres_transactions
USING
    model = {...},
    data = {
        "tables": ["postgres_ubereats.orders", "postgres_ubereats.invoices"]
        -- NO "knowledge_bases" section needed!
    },
    prompt_template = 'Expert with all knowledge embedded:
    
    BRAZILIAN TAX RATES:
    - ICMS: 17-18%
    - ISS: 2-5%  
    - PIS/COFINS: 3.65%
    
    YOUR DATA STATUS:
    - issued: 350 invoices
    - paid: 125 invoices
    
    COMPLIANCE RULES:
    - All transactions need fiscal notes
    - CNPJs must be format XX.XXX.XXX/XXXX-XX
    ';
```

---

## 🚀 **How to Create KB (If You Want Later)**

### **Step 1: Create Knowledge Base**
```sql
-- Example: Brazilian fiscal regulations
CREATE KNOWLEDGE_BASE brasil_fiscal_kb
FROM (
  SELECT 'ICMS - Imposto sobre Circulacao de Mercadorias e Servicos. Aliquotas variam entre 17-18% dependendo do estado brasileiro.' as content, 'icms_rules' as title
  UNION ALL
  SELECT 'ISS - Imposto sobre Servicos de Qualquer Natureza. Aplica-se sobre servicos como taxa de entrega, variando 2-5%.' as content, 'iss_rules' as title  
  UNION ALL
  SELECT 'PIS/COFINS - Contribuicoes federais sobre o faturamento. Aliquota combinada de 3.65%.' as content, 'pis_cofins_rules' as title
  UNION ALL
  SELECT 'Compliance: Todas as transacoes comerciais devem gerar nota fiscal eletronica (NFe) conforme legislacao brasileira.' as content, 'compliance_rules' as title
);
```

### **Step 2: Add to Agent**
```sql
CREATE AGENT agent_with_kb
USING
    model = {...},
    data = {
        "knowledge_bases": ["brasil_fiscal_kb"],  -- Reference the KB
        "tables": ["postgres_ubereats.invoices"]
    },
    prompt_template = 'Use knowledge base for Brazilian tax context...';
```

### **Step 3: Agent Automatically Uses KB**
The agent will automatically reference the knowledge base content when answering questions.

---

## 📋 **KB from Files (Advanced)**

### **Upload Documents:**
```sql
-- Create KB from uploaded files
CREATE KNOWLEDGE_BASE fiscal_docs_kb
FROM (
  SELECT * FROM FILES.fiscal_regulations_2024.pdf
  UNION ALL
  SELECT * FROM FILES.compliance_manual.docx
);
```

### **KB from URLs:**
```sql
-- Create KB from web content
CREATE KNOWLEDGE_BASE receita_federal_kb
FROM (
  SELECT content FROM WEB.get_content('https://receita.fazenda.gov.br/legislacao/icms')
);
```

---

## ✅ **Recommendation for Your Project**

### **Current Status: PERFECT ✅**
Your multi-agent setup is **complete and ready** without knowledge bases because:

1. **✅ Tax knowledge embedded** in agent prompts
2. **✅ Real data context included** (status counts, cities)
3. **✅ Compliance rules specified** (CNPJ format, fiscal notes)
4. **✅ No parsing errors** with current prompt sizes

### **Next Steps:**
1. **Deploy current agents** (no KB needed)
2. **Test with real questions**
3. **Add KB later** if you need:
   - Large tax regulation documents
   - Frequently changing policies
   - External compliance references

---

## 🎯 **Final Setup Commands (Ready to Use)**

```sql
-- Run this - NO KNOWLEDGE BASE required!
-- All agents have embedded knowledge

-- 1. Create PostgreSQL Agent
CREATE AGENT agent_postgres_transactions USING...

-- 2. Create MongoDB Agent  
CREATE AGENT agent_mongo_catalog USING...

-- 3. Create Supabase Agent
CREATE AGENT agent_supabase_realtime USING...

-- 4. Create Master Coordinator
CREATE AGENT agent_ubereats_coordinator USING...

-- 5. Test
SELECT answer FROM agent_ubereats_coordinator 
WHERE question = 'Relatorio de compliance fiscal por regiao';
```

**🚀 Your agents are production-ready without any knowledge base setup!** 🎯