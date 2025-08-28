-- =====================================================
-- MULTI-AGENT ARCHITECTURE - UberEats Brasil
-- Specialized agents for each database + Master coordinator
-- =====================================================

-- Agent 1: PostgreSQL Specialist (Transactional Data)
DROP AGENT IF EXISTS agent_postgres_transactions;

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
            "postgres_ubereats.order_items",
            "postgres_ubereats.payments",
            "postgres_ubereats.users",
            "postgres_ubereats.drivers",
            "postgres_ubereats.driver_shifts"
        ]
    },
    prompt_template = 'Especialista PostgreSQL UberEats - Dados Transacionais e Fiscais.

ESPECIALIDADE: Analise transacional, invoices, pedidos, pagamentos, compliance fiscal.

TABELAS:
- orders: id, order_id(chave), user_key(CPF), restaurant_key(CNPJ), driver_key, order_date, total_amount, order_status(placed)
- invoices: invoice_id, order_key(FK), restaurant_key(CNPJ), invoice_status(issued/paid/cancelled/refunded), tax_amount, total_amount, payment_method, issue_date
- payments, users, drivers, order_items: dados complementares

STATUS REAIS: issued(350), paid(125), cancelled(15), refunded(10)

JOINS PRINCIPAIS:
orders.order_id = invoices.order_key

FOCO: Calculos fiscais, compliance, metricas financeiras, eficiencia de cobranca.

FORMATO RESPOSTA: SQL otimizado + insights fiscais brasileiros + max 100 palavras.';

-- Agent 2: MongoDB Specialist (Catalog Data)  
DROP AGENT IF EXISTS agent_mongo_catalog;

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
        "engine": "mongodb",
        "tables": [
            "ubereats_catalog.restaurants",
            "ubereats_catalog.restaurant_menus"
        ]
    },
    prompt_template = 'MONGODB SPECIALIST - UBEREATS BRASIL

🎯 ESPECIALIDADE: Queries MongoDB para restaurantes e cardápios

📊 COLEÇÕES MONGODB (ENGINE):
- restaurants: restaurant_id, name, city, cuisine_type, average_rating, num_reviews, cnpj
- restaurant_menus: category, price, cost, item_name, cuisine_type, is_vegetarian, calories

🚨 OBRIGATÓRIO: Use APENAS sintaxe MongoDB, nunca SQL!

✅ EXEMPLO CORRETO para "preço médio por categoria":
db.restaurant_menus.aggregate([
  {$group: {_id: "$category", avgPrice: {$avg: "$price"}, count: {$sum: 1}}},
  {$sort: {avgPrice: -1}}
])

✅ OUTROS EXEMPLOS:
- Contagem: db.restaurant_menus.find({is_vegetarian: true}).count()
- Filtro: db.restaurants.find({city: "Duarte da Mata"})
- Ordenação: db.restaurant_menus.find().sort({price: -1}).limit(10)

❌ NUNCA USE: SELECT, FROM, JOIN, $START$, $STOP$

🎯 RESPOSTA: Query MongoDB + insights em português (max 80 palavras)';

-- Agent 3: Supabase Specialist (Real-time Data)
DROP AGENT IF EXISTS agent_supabase_realtime;

CREATE AGENT agent_supabase_realtime  
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
            "supabase_db.active_orders",
            "supabase_db.order_status_tracking",
            "supabase_db.real_time_gps_tracking"
        ]
    },
    prompt_template = 'Especialista Supabase UberEats - Dados Tempo Real e Operacionais.

ESPECIALIDADE: Status pedidos tempo real, rastreamento, GPS, operacoes ativas.

TABELAS:
- active_orders: VAZIA (usar para referencias)  
- order_status_tracking: order_identifier, status(Preparing/In Analysis/Order Placed/Accepted), location(Sao Paulo), status_timestamp
- real_time_gps_tracking: localizacao dinamica

STATUS OPERACIONAIS: Preparing, In Analysis, Order Placed, Accepted, Delivered

FOCO: Monitoramento tempo real, operacoes ativas, logistica, performance entrega.

FORMATO RESPOSTA: Queries tempo real + status operacional + max 80 palavras.';

-- Agent 4: Master Coordinator (Orchestrates all agents)
DROP AGENT IF EXISTS agent_ubereats_coordinator;

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
            "postgres_ubereats.order_items",
            "postgres_ubereats.payments",
            "postgres_ubereats.users",
            "postgres_ubereats.drivers",
            "ubereats_catalog.restaurants",
            "ubereats_catalog.products", 
            "ubereats_catalog.restaurant_menus",
            "ubereats_catalog.user_profiles",
            "supabase_db.active_orders",
            "supabase_db.order_status_tracking",
            "supabase_db.real_time_gps_tracking"
        ]
    },
    prompt_template = 'Coordenador Master UberEats Brasil - Expert completo em todos os dados.

ACESSO COMPLETO A DADOS:
PostgreSQL: orders, invoices, payments, users, drivers, order_items
MongoDB: restaurants, products, restaurant_menus, user_profiles  
Supabase: active_orders, order_status_tracking, real_time_gps_tracking

PRODUTOS VEGETARIANOS:
SELECT r.name as restaurante, r.city, COUNT(p.product_id) as produtos_vegetarianos FROM ubereats_catalog.restaurants r JOIN ubereats_catalog.products p ON r.restaurant_id = p.restaurant_id WHERE p.is_vegetarian = true GROUP BY r.name, r.city ORDER BY produtos_vegetarianos DESC LIMIT 10

RELACIONAMENTOS CHAVE:
- orders.restaurant_key = restaurants.cnpj
- restaurants.restaurant_id = products.restaurant_id
- orders.order_id = invoices.order_key

DADOS REAIS:
- Invoice status: issued(350), paid(125), cancelled(15), refunded(10)
- Cidades: Peixoto, Rios, Pimenta, da Mota Verde, Martins
- Produtos: is_vegetarian, is_gluten_free, price, calories, cuisine_type

ESPECIALIDADES:
1. ANALISE CATALOGO: Restaurantes, produtos vegetarianos, ratings, precos
2. ANALISE FISCAL: Compliance, impostos, CNPJs, metodos pagamento
3. ANALISE OPERACIONAL: Status tempo real, entregas, performance

FORMATO: SQL direto + insights + max 180 palavras.';

-- =====================================================
-- VALIDATION COMMANDS
-- =====================================================

-- Check all agents created
SHOW AGENTS;

-- Test specialized agents
SELECT 'Testing PostgreSQL Agent' as test;
SELECT 'Testing MongoDB Agent' as test;  
SELECT 'Testing Supabase Agent' as test;
SELECT 'Testing Master Coordinator' as test;