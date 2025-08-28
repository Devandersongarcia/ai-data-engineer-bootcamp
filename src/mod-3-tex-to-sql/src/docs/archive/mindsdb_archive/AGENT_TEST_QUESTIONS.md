# 🧠 Brasil UberEats Data Expert - Test Questions

Este arquivo contém perguntas estratégicas para testar as capacidades completas do **agent_brasil_ubereats_expert**, explorando todos os bancos de dados disponíveis.

---

## 📊 **ANÁLISE FISCAL & COMPLIANCE**

### Questões Tributárias Avançadas
```
1. "Qual o total de impostos recolhidos por região no último mês? Inclua breakdown por tipo de taxa."

2. "Identifique restaurantes com possíveis inconsistências fiscais - compare faturamento vs impostos pagos."

3. "Gere relatório de compliance fiscal: restaurantes por estado, CNPJs válidos, e situação das notas fiscais."

4. "Calcule a carga tributária efetiva por tipo de cozinha - qual segmento paga mais impostos proporcionalmente?"
```

---

## 💰 **BUSINESS INTELLIGENCE AVANÇADO**

### KPIs e Métricas Estratégicas
```
5. "Dashboard executivo: top 10 restaurantes por faturamento, AOV, frequência de pedidos e margem líquida."

6. "Análise de sazonalidade: como variam as vendas por tipo de cozinha ao longo dos meses? Identifique padrões."

7. "Customer Lifetime Value: segmente usuários por valor total gasto e identifique perfis de alto valor."

8. "Performance de entregadores: rankeie por eficiência, pontualidade e valor médio de gorjetas recebidas."
```

### Análise Cross-Database
```
9. "Correlacione dados de catálogo com performance: restaurantes com mais produtos vegetarianos vendem mais?"

10. "Combine dados tempo real + histórico: qual a precisão das estimativas de entrega vs tempo real?"

11. "Análise de produtos: itens mais vendidos por região, considerando preferências locais e preços."
```

---

## 🚚 **ANÁLISE OPERACIONAL DETALHADA**

### Eficiência e Logística
```
12. "Otimização de turnos: analise performance dos entregadores por horário - quando são mais eficientes?"

13. "Mapeamento de demanda: quais áreas têm mais pedidos ativos em tempo real? Sugira redistribuição de entregadores."

14. "Análise de cancelamentos: identifique padrões nos pedidos cancelados - restaurante, horário, valor, região."

15. "Tempo de preparo vs realidade: compare tempo estimado dos produtos com dados reais de entrega."
```

---

## 🔍 **BUSCA SEMÂNTICA E RECOMENDAÇÕES**

### Inteligência de Cardápio
```
16. "Busque pratos similares a 'feijoada' nos cardápios e analise preços e popularidade regional."

17. "Identifique oportunidades de cross-sell: que produtos complementares são pedidos juntos?"

18. "Análise nutricional: restaurantes com mais opções saudáveis (baixa caloria, vegano) por região."

19. "Sazonalidade de cardápio: que tipos de pratos vendem mais no inverno vs verão?"
```

---

## 📈 **ANÁLISES PREDITIVAS E INSIGHTS**

### Inteligência de Mercado
```
20. "Preveja demanda: baseado no histórico, quais restaurantes precisarão de mais entregadores amanhã?"

21. "Análise de churn: identifique usuários em risco de abandonar a plataforma baseado em padrões de pedidos."

22. "Oportunidades de crescimento: regiões sub-atendidas com alto potencial de demanda."

23. "Precificação inteligente: analise se restaurantes premium justificam preços com qualidade de serviço."
```

---

## 🎯 **CASOS DE USO COMPLEXOS**

### Análises Multi-Dimensionais
```
24. "Relatório 360°: Para o restaurante 'Nogueira Restaurante', combine dados de catálogo, vendas, impostos, avaliações e tempo real."

25. "Impacto do clima: correlacione dados de entrega com condições meteorológicas (use dados externos se disponíveis)."

26. "Análise competitiva: compare performance de restaurantes similares na mesma região - preços, tempo, avaliações."

27. "ROI de marketing: qual tipo de cozinha tem melhor retorno em campanhas promocionais?"
```

---

## 🚀 **TESTE DE INTEGRAÇÃO COMPLETA**

### Queries Avançadas Cross-Database
```
28. "Construa um data mart virtual combinando todos os bancos: orders, invoices, products, real-time tracking."

29. "Pipeline de métricas em tempo real: monitore KPIs que atualizam automaticamente com novos pedidos."

30. "Auditoria completa: valide consistência de dados entre PostgreSQL, MongoDB e Supabase para um período específico."
```

---

## 📋 **COMO USAR ESTE GUIA**

### 🎯 **Teste Progressivo:**
1. **Básico**: Comece com questões 1-10 (fiscal e BI simples)
2. **Intermediário**: Questões 11-20 (cross-database e operacional)  
3. **Avançado**: Questões 21-30 (preditivo e integração completa)

### 💡 **Dicas de Teste:**
- **Observe a velocidade** de resposta do agente
- **Verifique a precisão** das consultas SQL geradas
- **Analise a qualidade** dos insights fornecidos
- **Teste edge cases** como dados ausentes ou inconsistentes

### 📊 **Métricas de Sucesso:**
- ✅ **Consultas SQL válidas** e otimizadas
- ✅ **Insights acionáveis** para o negócio
- ✅ **Compliance fiscal** brasileiro
- ✅ **Integração seamless** entre bases de dados
- ✅ **Respostas em português** claro e conciso

---

## 🔧 **COMANDOS DE TESTE RÁPIDO**

```bash
# Inicie o chat app
PYTHONPATH=src/mindsdb streamlit run src/mindsdb/apps/chat_app.py --server.port 8502

# Acesse no browser
open http://localhost:8502
```

---

**🧠 Pronto para testar a inteligência do seu agente UberEats!** 🇧🇷