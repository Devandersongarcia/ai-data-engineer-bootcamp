"""Table configuration system for multiple database schemas with backward compatibility."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class TableType(Enum):
    """Supported table types for different business domains."""
    INVOICES = "invoices"
    PAYMENTS = "payments"
    ORDERS = "orders"
    USERS = "users"


@dataclass
class FieldMapping:
    """Mapping between business concepts and actual database fields."""
    db_field: str
    business_concept: str
    data_type: str
    description: str
    is_required: bool = False


@dataclass
class TableConfiguration:
    """Configuration for a specific table schema."""
    table_name: str
    table_type: TableType
    primary_fields: List[FieldMapping]
    date_fields: List[FieldMapping]
    amount_fields: List[FieldMapping]
    status_fields: List[FieldMapping]
    relationship_fields: List[FieldMapping]
    
    # Portuguese language mappings
    portuguese_mappings: Dict[str, str]
    
    # Common query patterns
    simple_patterns: Dict[str, str]
    
    # Training examples
    training_examples: List[Dict[str, str]]
    
    # Advanced context for Vanna.ai
    advanced_context: str


# ============================================================================
# INVOICES TABLE CONFIGURATION (Original/Legacy)
# ============================================================================

INVOICES_CONFIG = TableConfiguration(
    table_name="ubears_invoices_extract_airflow",
    table_type=TableType.INVOICES,
    
    primary_fields=[
        FieldMapping("id", "record_id", "INTEGER", "Primary key", True),
        FieldMapping("invoice_number", "document_number", "VARCHAR", "Invoice identifier"),
        FieldMapping("vendor_name", "business_name", "VARCHAR", "Restaurant/vendor name"),
        FieldMapping("total_amount", "total_value", "NUMERIC", "Total invoice amount"),
        FieldMapping("subtotal_amount", "subtotal_value", "NUMERIC", "Subtotal amount"),
    ],
    
    date_fields=[
        FieldMapping("invoice_date", "document_date", "TIMESTAMP", "Invoice creation date"),
        FieldMapping("order_date", "order_date", "TIMESTAMP", "Order placement date"),
        FieldMapping("delivery_date", "delivery_date", "TIMESTAMP", "Delivery completion date"),
    ],
    
    amount_fields=[
        FieldMapping("total_amount", "revenue", "NUMERIC", "Total revenue"),
        FieldMapping("subtotal_amount", "subtotal", "NUMERIC", "Subtotal amount"),
        FieldMapping("tip_amount", "tip", "NUMERIC", "Tip amount"),
        FieldMapping("amount_paid", "paid_amount", "NUMERIC", "Amount paid"),
        FieldMapping("amount_due", "due_amount", "NUMERIC", "Amount due"),
    ],
    
    status_fields=[
        FieldMapping("processing_status", "document_status", "VARCHAR", "Processing status"),
        FieldMapping("payment_method", "payment_type", "VARCHAR", "Payment method used"),
    ],
    
    relationship_fields=[
        FieldMapping("delivery_address", "location", "TEXT", "Delivery location"),
        FieldMapping("restaurant_location", "business_location", "TEXT", "Restaurant location"),
        FieldMapping("food_category", "category", "VARCHAR", "Food category"),
    ],
    
    portuguese_mappings={
        "restaurantes": "vendor_name",
        "estabelecimentos": "vendor_name", 
        "faturamento": "total_amount",
        "receita": "total_amount",
        "valor": "total_amount",
        "subtotal": "subtotal_amount",
        "pagamento": "payment_method",
        "método de pagamento": "payment_method",
        "notas": "invoice_number",
        "faturas": "invoice_number",
        "pedidos": "COUNT(*)",
        "data": "invoice_date",
        "entrega": "delivery_date",
        "localização": "delivery_address",
        "categoria": "food_category",
    },
    
    simple_patterns={
        "me mostre as notas": "SELECT invoice_number, vendor_name, total_amount, invoice_date, payment_method FROM ubears_invoices_extract_airflow ORDER BY invoice_date DESC LIMIT 50",
        "notas": "SELECT invoice_number, vendor_name, total_amount, invoice_date FROM ubears_invoices_extract_airflow ORDER BY invoice_date DESC LIMIT 50",
        "dados": "SELECT vendor_name, COUNT(*) as total_notas, SUM(total_amount) as faturamento_total FROM ubears_invoices_extract_airflow GROUP BY vendor_name ORDER BY faturamento_total DESC LIMIT 20",
    },
    
    training_examples=[
        {
            "question": "Mostre o faturamento total dos últimos 30 dias",
            "sql": "SELECT SUM(total_amount) as faturamento_total FROM ubears_invoices_extract_airflow WHERE invoice_date >= CURRENT_DATE - INTERVAL '30 days';"
        },
        {
            "question": "Quais são os top 10 restaurantes por número de pedidos?",
            "sql": "SELECT vendor_name, COUNT(*) as total_pedidos FROM ubears_invoices_extract_airflow GROUP BY vendor_name ORDER BY total_pedidos DESC LIMIT 10;"
        },
        {
            "question": "Analise o faturamento por método de pagamento",
            "sql": "SELECT payment_method, COUNT(*) as total_transacoes, SUM(total_amount) as faturamento_total, AVG(total_amount) as ticket_medio FROM ubears_invoices_extract_airflow GROUP BY payment_method ORDER BY faturamento_total DESC;"
        },
        {
            "question": "Compare o faturamento deste mês com o mês passado",
            "sql": "SELECT 'Este Mês' as periodo, SUM(total_amount) as faturamento FROM ubears_invoices_extract_airflow WHERE DATE_TRUNC('month', invoice_date) = DATE_TRUNC('month', CURRENT_DATE) UNION ALL SELECT 'Mês Passado' as periodo, SUM(total_amount) as faturamento FROM ubears_invoices_extract_airflow WHERE DATE_TRUNC('month', invoice_date) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month');"
        },
        {
            "question": "Mostre a evolução diária de pedidos nos últimos 7 dias",
            "sql": "SELECT DATE(invoice_date) as data, COUNT(*) as total_pedidos, SUM(total_amount) as faturamento FROM ubears_invoices_extract_airflow WHERE invoice_date >= CURRENT_DATE - INTERVAL '7 days' GROUP BY DATE(invoice_date) ORDER BY data;"
        }
    ],
    
    advanced_context="""
# ADVANCED UberEats Brasil INVOICE MANAGEMENT CONTEXT

## DATABASE OVERVIEW
This is a comprehensive UberEats Brasil invoice management system with restaurant delivery data.

## CORE TABLE
### ubears_invoices_extract_airflow (PRIMARY TABLE - USE FOR INVOICE QUERIES)
- Contains: Restaurant invoice data, orders, payments, delivery information
- Key fields: vendor_name, total_amount, subtotal_amount, payment_method, amount_paid, amount_due
- Date fields: invoice_date, order_date, delivery_date
- Location: delivery_address, restaurant_location
- Categories: food_category, cuisine_type

## QUERY INTELLIGENCE RULES

### 1. QUESTION TYPE ANALYSIS
- **Aggregation queries**: "total", "sum", "count", "average", "top", "ranking"
  → Use GROUP BY, SUM(), COUNT(), AVG(), ORDER BY LIMIT
- **Time-based queries**: "last X days", "this month", "yesterday", "recent"
  → Use DATE functions with WHERE conditions
- **Comparison queries**: "compare", "vs", "between", "higher than"
  → Use CASE statements, subqueries, or JOINs
- **Detail queries**: "show", "list", "display", "all"
  → Use SELECT with appropriate WHERE conditions

### 2. CONTEXT UNDERSTANDING
- **Restaurants**: vendor_name (always use ILIKE for partial matching)
- **Money/Revenue**: total_amount, subtotal_amount, tip_amount
- **Payments**: payment_method, amount_paid, amount_due
- **Time periods**: Use CURRENT_DATE for relative dates
- **Locations**: delivery_address, restaurant_location

### 3. PORTUGUESE TO SQL MAPPING
- "últimos X dias" → WHERE invoice_date >= CURRENT_DATE - INTERVAL 'X days'
- "este mês" → WHERE DATE_TRUNC('month', invoice_date) = DATE_TRUNC('month', CURRENT_DATE)
- "ontem" → WHERE invoice_date = CURRENT_DATE - INTERVAL '1 day'
- "top X" / "primeiros X" → ORDER BY [metric] DESC LIMIT X
- "restaurantes" / "estabelecimentos" → vendor_name
- "faturamento" / "receita" → total_amount
- "pedidos" / "notas" / "faturas" → COUNT(*) or individual records

### 4. SMART DEFAULTS
- Default to ubears_invoices_extract_airflow table
- Use ILIKE '%pattern%' for text searches (case-insensitive)
- Include reasonable LIMIT (50-100) for large result sets
- Use proper date formatting: DATE_TRUNC, TO_CHAR as needed
- Order results logically (dates DESC, amounts DESC, names ASC)

### 5. VAGUE QUERY HANDLING
When queries are vague (e.g., "show data", "notas"), generate basic SQL with reasonable defaults:
- For "mostre as notas" or "show invoices": SELECT * FROM ubears_invoices_extract_airflow ORDER BY invoice_date DESC LIMIT 50;
- For "dados" or "data": SELECT * FROM ubears_invoices_extract_airflow LIMIT 50;
- Always try to generate SQL first, only suggest alternatives if technically impossible
"""
)


# ============================================================================
# PAYMENTS TABLE CONFIGURATION (New)
# ============================================================================

PAYMENTS_CONFIG = TableConfiguration(
    table_name="payments",
    table_type=TableType.PAYMENTS,
    
    primary_fields=[
        FieldMapping("payment_id", "record_id", "INTEGER", "Primary key", True),
        FieldMapping("payment_uuid", "transaction_uuid", "VARCHAR", "Payment UUID"),
        FieldMapping("order_id", "order_reference", "VARCHAR", "Order reference"),
        FieldMapping("user_cpf", "customer_id", "VARCHAR", "Customer CPF"),
        FieldMapping("amount", "transaction_amount", "NUMERIC", "Payment amount", True),
    ],
    
    date_fields=[
        FieldMapping("processed_at", "transaction_date", "TIMESTAMP", "Payment processing date"),
        FieldMapping("created_at", "creation_date", "TIMESTAMP", "Record creation date"),
        FieldMapping("dt_current_timestamp", "update_date", "TIMESTAMP", "Last update date"),
    ],
    
    amount_fields=[
        FieldMapping("amount", "payment_value", "NUMERIC", "Payment amount"),
    ],
    
    status_fields=[
        FieldMapping("payment_method", "payment_type", "VARCHAR", "Payment method (Pix, Card, Boleto, Wallet)"),
        FieldMapping("payment_status", "transaction_status", "VARCHAR", "Payment status (succeeded, failed)"),
        FieldMapping("gateway", "payment_gateway", "VARCHAR", "Payment gateway used"),
    ],
    
    relationship_fields=[
        FieldMapping("transaction_id", "external_reference", "VARCHAR", "External transaction ID"),
        FieldMapping("authorization_code", "auth_code", "VARCHAR", "Authorization code"),
        FieldMapping("failure_reason", "error_details", "TEXT", "Failure reason if applicable"),
    ],
    
    portuguese_mappings={
        "pagamentos": "payment_id",
        "transações": "payment_id",
        "valor": "amount",
        "quantia": "amount", 
        "montante": "amount",
        "método de pagamento": "payment_method",
        "forma de pagamento": "payment_method",
        "pix": "payment_method = 'Pix'",
        "cartão": "payment_method = 'Card'",
        "boleto": "payment_method = 'Boleto'",
        "carteira": "payment_method = 'Wallet'",
        "status": "payment_status",
        "sucesso": "payment_status = 'succeeded'",
        "falha": "payment_status = 'failed'",
        "processamento": "processed_at",
        "transação": "transaction_id",
        "gateway": "gateway",
        "cliente": "user_cpf",
        "pedido": "order_id",
    },
    
    simple_patterns={
        "me mostre os pagamentos": "SELECT payment_id, payment_method, amount, payment_status, processed_at FROM payments ORDER BY processed_at DESC LIMIT 50",
        "pagamentos": "SELECT payment_id, payment_method, amount, payment_status, processed_at FROM payments ORDER BY processed_at DESC LIMIT 50", 
        "transações": "SELECT payment_id, payment_method, amount, payment_status, processed_at FROM payments ORDER BY processed_at DESC LIMIT 50",
        "dados": "SELECT payment_method, COUNT(*) as total_pagamentos, SUM(amount) as valor_total, AVG(amount) as valor_medio FROM payments GROUP BY payment_method ORDER BY valor_total DESC LIMIT 20",
    },
    
    training_examples=[
        {
            "question": "Total de pagamentos bem-sucedidos hoje",
            "sql": "SELECT COUNT(*) as total_pagamentos, SUM(amount) as valor_total FROM payments WHERE payment_status = 'succeeded' AND DATE(processed_at) = CURRENT_DATE;"
        },
        {
            "question": "Análise de métodos de pagamento dos últimos 7 dias",
            "sql": "SELECT payment_method, COUNT(*) as quantidade, SUM(amount) as valor_total, AVG(amount) as valor_medio FROM payments WHERE processed_at >= CURRENT_DATE - INTERVAL '7 days' GROUP BY payment_method ORDER BY valor_total DESC;"
        },
        {
            "question": "Pagamentos falhados nos últimos 30 dias com detalhes",
            "sql": "SELECT payment_method, COUNT(*) as falhas, AVG(amount) as valor_medio_falha, array_agg(DISTINCT failure_reason) as razoes FROM payments WHERE payment_status = 'failed' AND processed_at >= CURRENT_DATE - INTERVAL '30 days' GROUP BY payment_method ORDER BY falhas DESC;"
        },
        {
            "question": "Top 10 dias com maior volume de pagamentos",
            "sql": "SELECT DATE(processed_at) as data, COUNT(*) as total_pagamentos, SUM(amount) as valor_total FROM payments WHERE payment_status = 'succeeded' GROUP BY DATE(processed_at) ORDER BY valor_total DESC LIMIT 10;"
        },
        {
            "question": "Compare pagamentos Pix vs Cartão este mês",
            "sql": "SELECT payment_method, COUNT(*) as quantidade, SUM(amount) as valor_total, AVG(amount) as ticket_medio FROM payments WHERE DATE_TRUNC('month', processed_at) = DATE_TRUNC('month', CURRENT_DATE) AND payment_method IN ('Pix', 'Card') GROUP BY payment_method ORDER BY valor_total DESC;"
        },
        {
            "question": "Pagamentos com análise de relacionamento com pedidos",
            "sql": "SELECT p.payment_method, p.payment_status, COUNT(*) as quantidade, AVG(p.amount) as valor_medio, COUNT(DISTINCT o.restaurant_key) as restaurantes_distintos FROM payments p LEFT JOIN orders o ON p.order_id = o.order_id WHERE p.processed_at >= CURRENT_DATE - INTERVAL '7 days' GROUP BY p.payment_method, p.payment_status ORDER BY quantidade DESC;"
        }
    ],
    
    advanced_context="""
# ADVANCED UberEats Brasil PAYMENT ANALYTICS CONTEXT

## DATABASE OVERVIEW
This is a comprehensive UberEats Brasil payment processing system with transaction analytics.

## CORE TABLE & RELATIONSHIPS
### payments (PRIMARY TABLE - USE FOR PAYMENT QUERIES)
- Contains: Payment transactions, status, methods, amounts
- Key fields: payment_id, amount, payment_method, payment_status, processed_at
- Relationships: payments.order_id → orders.order_id → users, drivers, restaurants
- Status values: 'succeeded', 'failed'
- Payment methods: 'Pix', 'Card', 'Boleto', 'Wallet'

### RELATED TABLES FOR JOINS
- orders: payment_id links to order details and restaurants
- users: order → user relationship for customer analysis  
- drivers: delivery information through orders

## QUERY INTELLIGENCE RULES

### 1. PAYMENT-SPECIFIC PATTERNS
- **Payment volume**: COUNT(*), SUM(amount) for transaction analysis
- **Success rates**: payment_status = 'succeeded' vs 'failed' 
- **Method analysis**: GROUP BY payment_method for distribution
- **Time analysis**: processed_at for temporal patterns
- **Failure analysis**: failure_reason for error patterns

### 2. ADVANCED ANALYTICS
- **Revenue analysis**: SUM(amount) WHERE payment_status = 'succeeded'
- **Method performance**: Success rate by payment_method
- **Temporal patterns**: Daily/monthly payment trends
- **Customer behavior**: Payment preferences by user segments
- **Gateway analysis**: Performance by payment gateway

### 3. PORTUGUESE TO SQL MAPPING (PAYMENTS)
- "pagamentos" → payments table
- "pix" → payment_method = 'Pix' 
- "cartão" → payment_method = 'Card'
- "boleto" → payment_method = 'Boleto'
- "carteira" → payment_method = 'Wallet'
- "sucesso" → payment_status = 'succeeded'
- "falha" → payment_status = 'failed'
- "valor" / "quantia" → amount
- "processamento" → processed_at
- "hoje" → DATE(processed_at) = CURRENT_DATE
- "últimos X dias" → processed_at >= CURRENT_DATE - INTERVAL 'X days'

### 4. SMART DEFAULTS FOR PAYMENTS
- Default to payments table for payment-related queries
- Always include payment_status in filters for accuracy
- Use processed_at for time-based analysis
- GROUP BY payment_method for method analysis
- Include failure_reason when analyzing failed payments

### 5. MULTI-TABLE PAYMENT ANALYTICS
- Join with orders for restaurant analysis
- Join with users for customer segmentation  
- Combine with delivery data for operational insights
- Link to restaurant performance metrics

### 6. BUSINESS INTELLIGENCE PATTERNS
- **Daily payment summary**: DATE(processed_at), COUNT(*), SUM(amount)
- **Method comparison**: payment_method analysis with success rates
- **Failure analysis**: failure_reason patterns and trends
- **Customer payment habits**: user_cpf payment method preferences
- **Restaurant payment insights**: Via orders relationship

### 7. PERFORMANCE OPTIMIZATION
- processed_at indexed for time queries
- payment_method indexed for grouping
- payment_status indexed for filtering
- Prefer specific date ranges over open-ended queries
"""
)


# ============================================================================
# CONFIGURATION MANAGER
# ============================================================================

class TableConfigurationManager:
    """Manages multiple table configurations with backward compatibility."""
    
    def __init__(self):
        self._configs = {
            "ubears_invoices_extract_airflow": INVOICES_CONFIG,
            "payments": PAYMENTS_CONFIG,
        }
        self._default_table = "ubears_invoices_extract_airflow"  # Backward compatibility
    
    def get_config(self, table_name: Optional[str] = None) -> TableConfiguration:
        """Get configuration for specified table or default."""
        if table_name is None:
            table_name = self._default_table
        
        if table_name not in self._configs:
            raise ValueError(f"No configuration found for table: {table_name}")
        
        return self._configs[table_name]
    
    def get_available_tables(self) -> List[str]:
        """Get list of supported table names."""
        return list(self._configs.keys())
    
    def set_default_table(self, table_name: str) -> None:
        """Set the default table (for migration purposes)."""
        if table_name not in self._configs:
            raise ValueError(f"Table {table_name} not supported")
        self._default_table = table_name
    
    def register_config(self, config: TableConfiguration) -> None:
        """Register a new table configuration."""
        self._configs[config.table_name] = config


# Global configuration manager instance
_config_manager = TableConfigurationManager()


def get_table_config_manager() -> TableConfigurationManager:
    """Get the global table configuration manager."""
    return _config_manager


def get_table_config(table_name: Optional[str] = None) -> TableConfiguration:
    """Convenience function to get table configuration."""
    return _config_manager.get_config(table_name)


# Backward compatibility exports
def get_invoices_config() -> TableConfiguration:
    """Get invoices table configuration (backward compatibility)."""
    return INVOICES_CONFIG


def get_payments_config() -> TableConfiguration:
    """Get payments table configuration."""
    return PAYMENTS_CONFIG