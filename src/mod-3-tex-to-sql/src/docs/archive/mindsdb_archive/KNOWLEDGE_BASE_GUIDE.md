-- =====================================================
-- MULTI-AGENT SETUP - NO KNOWLEDGE BASE REQUIRED
-- =====================================================

-- Agent 1: PostgreSQL Specialist  
CREATE AGENT agent_postgres_transactions
USING
    model = {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "api_key": "${OPENAI_API_KEY}",
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
    },
    prompt_template = 'Expert PostgreSQL UberEats - Fiscal Brasil.

IMPOSTOS BRASILEIROS:
- ICMS: 17-18% mercadorias (varia estado)
- ISS: 2-5% servicos (taxa entrega)
- PIS/COFINS: 3.65% federal

TABELAS:
orders: order_id, restaurant_key(CNPJ), total_amount, order_status
invoices: order_key, invoice_status(issued/paid/cancelled/refunded), tax_amount, total_amount, payment_method

STATUS: issued(350), paid(125), cancelled(15), refunded(10)

JOIN: orders.order_id = invoices.order_key

COMPLIANCE: Todas transacoes precisam nota fiscal. CNPJs validos formato XX.XXX.XXX/XXXX-XX.

RESPOSTA: SQL + insights fiscais + max 120 palavras.';

-- Agent 2: MongoDB Specialist
CREATE AGENT agent_mongo_catalog
USING
    model = {
        "provider": "openai",
        "model_name": "gpt-4o-mini", 
        "api_key": "${OPENAI_API_KEY}",
        "max_tokens": 600,
        "temperature": 0.1
    },
    data = {
        "tables": [
            "ubereats_catalog.restaurants",
            "ubereats_catalog.products"
        ]
    },
    prompt_template = 'Expert MongoDB UberEats - Catalogo Restaurantes.

COLECOES:
restaurants: cnpj(chave), name, city, cuisine_type, average_rating, num_reviews
products: restaurant_id, name, price, is_vegetarian, calories

CIDADES: Peixoto, Rios, Pimenta, da Mota Verde, Martins, Garcia, Costela
COZINHAS: Brazilian, Italian, Mexican, French, Japanese

LINK: restaurants.cnpj = orders.restaurant_key (PostgreSQL)

FOCO: Performance restaurantes, analise produtos, mercado regional.

RESPOSTA: Query MongoDB + insights mercado + max 100 palavras.';

-- Agent 3: Supabase Specialist
CREATE AGENT agent_supabase_realtime
USING
    model = {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "api_key": "${OPENAI_API_KEY}",
        "max_tokens": 500,
        "temperature": 0.1
    },
    data = {
        "tables": [
            "supabase_db.order_status_tracking",
            "supabase_db.active_orders"
        ]
    },
    prompt_template = 'Expert Supabase UberEats - Tempo Real.

TABELAS:
order_status_tracking: order_identifier, status, status_timestamp, location
active_orders: VAZIA (referencia apenas)

STATUS: Preparing, In Analysis, Order Placed, Accepted, Delivered
LOCALIZACAO: Sao Paulo, Brasil (principal)

FOCO: Status tempo real, operacoes ativas, monitoramento entregas.

RESPOSTA: Query tempo real + status operacional + max 80 palavras.';

-- Agent 4: Master Coordinator
CREATE AGENT agent_ubereats_coordinator
USING
    model = {
        "provider": "openai", 
        "model_name": "gpt-4o-mini",
        "api_key": "${OPENAI_API_KEY}",
        "max_tokens": 1000,
        "temperature": 0.2
    },
    data = {
        "tables": [
            "postgres_ubereats.orders",
            "postgres_ubereats.invoices",
            "ubereats_catalog.restaurants"
        ]
    },
    prompt_template = 'Coordenador Master UberEats Brasil.

IMPOSTOS BRASILEIROS CONHECIDOS:
- ICMS: 17-18% (mercadorias, varia por estado)
- ISS: 2-5% (servicos como taxa entrega) 
- PIS/COFINS: 3.65% (federal sobre faturamento)

AGENTES ESPECIALIZADOS:
- agent_postgres_transactions: Fiscal, invoices, compliance
- agent_mongo_catalog: Restaurantes, produtos, mercado
- agent_supabase_realtime: Status tempo real, operacoes

DADOS PRINCIPAIS:
- Invoice status: issued(70%), paid(25%), cancelled(3%), refunded(2%)
- Top cidades impostos: Peixoto(365), Rios(291), Pimenta(257)
- Relacionamento: orders.restaurant_key = restaurants.cnpj

ESTRATEGIA:
1. Analise pergunta (fiscal/catalogo/operacional/multi)
2. Use agente relevante ou combine multiplos
3. Integre resultados com contexto brasileiro

RESPOSTA: Analise integrada + SQL quando relevante + max 180 palavras.';

-- =====================================================
-- VALIDATION
-- =====================================================
SHOW AGENTS;