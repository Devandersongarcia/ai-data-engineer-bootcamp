-- =====================================================
-- BRASIL INVOICE EXPERT - SECURE SETUP TEMPLATE
-- Use this template and replace placeholder values
-- =====================================================

-- Step 1: Create PostgreSQL Connection
-- REPLACE WITH YOUR ACTUAL DATABASE CREDENTIALS
CREATE DATABASE postgres_ubereats
WITH ENGINE = 'postgres',
PARAMETERS = {
    "host": "${POSTGRES_HOST}",
    "port": ${POSTGRES_PORT},
    "database": "${POSTGRES_DATABASE}",
    "user": "${POSTGRES_USER}",
    "password": "${POSTGRES_PASSWORD}"
};

-- Step 2: Create MongoDB Connection for UberEats Catalog
CREATE DATABASE ubereats_catalog
WITH ENGINE = 'mongodb',
PARAMETERS = {
    "host": "${MONGODB_CONNECTION_STRING}",
    "database": "ubereats_catalog"
};

-- Step 3: Create Supabase Connection 
CREATE DATABASE supabase_db
WITH ENGINE = 'supabase',
PARAMETERS = {
    "host": "${SUPABASE_HOST}",
    "port": ${SUPABASE_PORT},
    "database": "${SUPABASE_DATABASE}",
    "user": "${SUPABASE_USER}",
    "password": "${SUPABASE_PASSWORD}"
};

-- Step 4: Create Qdrant Connection for Restaurant Menus (Optional)
-- REPLACE WITH YOUR ACTUAL QDRANT CREDENTIALS IF NEEDED
CREATE DATABASE brasil_qdrant_menus
WITH ENGINE = 'qdrant',
PARAMETERS = {
    "location": "YOUR_QDRANT_URL",
    "api_key": "YOUR_QDRANT_API_KEY",
    "collection_name": "restaurant_menus"
};

-- Step 5: Create Brasil UberEats Data Expert Agent
-- REPLACE YOUR_OPENAI_API_KEY WITH YOUR ACTUAL KEY
CREATE AGENT agent_brasil_ubereats_expert
USING
    model = {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "api_key": "${OPENAI_API_KEY}",
        "max_tokens": 1200,
        "temperature": 0.2
    },
    data = {
        "knowledge_bases": ["brasil_invoice_kb"],
        "tables": [
            "postgres_ubereats.orders",
            "postgres_ubereats.invoices", 
            "postgres_ubereats.order_items",
            "postgres_ubereats.payments",
            "postgres_ubereats.users",
            "postgres_ubereats.drivers",
            "postgres_ubereats.driver_shifts",
            "postgres_ubereats.ubears_invoices_extract_airflow",
            "ubereats_catalog.restaurants",
            "ubereats_catalog.products", 
            "ubereats_catalog.restaurant_menus",
            "ubereats_catalog.user_profiles",
            "supabase_db.active_orders",
            "supabase_db.order_status_tracking",
            "supabase_db.real_time_gps_tracking",
            "brasil_qdrant_menus.restaurant_menus"
        ]
    },
    prompt_template = 'Expert UberEats Brasil: SQL, BI, Compliance Fiscal.

DADOS:
PostgreSQL: orders (id, order_id, user_key, restaurant_key, driver_key, order_date, total_amount, order_status), invoices (invoice_id, order_key, user_key, restaurant_key, invoice_status: issued/paid/cancelled/refunded, subtotal, tax_amount, total_amount, payment_method)

MongoDB: restaurants (cnpj, name, city, cuisine_type), products (restaurant_id, name, price, is_vegetarian)

Supabase: order_status_tracking (order_identifier, status, location)

RELACIONAMENTOS:
orders.order_id = invoices.order_key
orders.restaurant_key = restaurants.cnpj

STATUS REAIS:
Invoice: issued(350), paid(125), cancelled(15), refunded(10)
Orders: placed(500)

CIDADES: Peixoto, Rios, Pimenta, da Mota Verde, Martins, Duarte da Mata

COMPLIANCE FISCAL:
SELECT r.city, r.cnpj, r.name, COUNT(i.invoice_id) AS notas, SUM(CASE WHEN i.invoice_status = issued THEN 1 ELSE 0 END) AS emitidas, SUM(CASE WHEN i.invoice_status = paid THEN 1 ELSE 0 END) AS pagas, SUM(i.tax_amount) AS impostos, ROUND(AVG(i.tax_amount/i.total_amount*100), 2) AS percentual_imposto FROM ubereats_catalog.restaurants r LEFT JOIN postgres_ubereats.orders o ON r.cnpj = o.restaurant_key LEFT JOIN postgres_ubereats.invoices i ON o.order_id = i.order_key WHERE r.cnpj IS NOT NULL GROUP BY r.city, r.cnpj, r.name HAVING COUNT(i.invoice_id) > 0 ORDER BY impostos DESC LIMIT 20

REGRAS:
- Use JOINs corretos
- Sempre LIMIT 50
- Status exatos: issued, paid, cancelled, refunded
- Analise regional por city
- Portugues brasileiro
- Max 150 palavras + SQL';

-- =====================================================
-- VALIDATION COMMANDS
-- =====================================================

-- Check connections
SHOW DATABASES;

-- Check agent cr
     --
     -- eation
SHOW AGENTS;

-- Test tables access
SHOW TABLES FROM postgres_railway;
SHOW TABLES FROM ubereats_catalog;
SHOW TABLES FROM supabase_db;
SHOW TABLES FROM brasil_qdrant_menus;