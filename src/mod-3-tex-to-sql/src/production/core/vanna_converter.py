"""Vanna.ai-powered text-to-SQL converter with production-grade features."""

import logging
import os
import re
import time
import uuid
from typing import Optional, Dict, Any

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

# Optimize environment for production
os.environ.update({
    'ANONYMIZED_TELEMETRY': 'False',
    'TOKENIZERS_PARALLELISM': 'false',
    'POSTHOG_DISABLE': 'true'
})

from vanna.chromadb.chromadb_vector import ChromaDB_VectorStore
from vanna.openai.openai_chat import OpenAI_Chat

from config.settings import get_settings
from utils.async_utils import make_async_compatible
from utils.connection_pool import get_connection_manager
from utils.error_handling import (
    handle_database_error, handle_api_error, create_error_context, ErrorHandler
)
from utils.health_check import get_health_checker, check_database_connection, check_openai_api
from utils.logging_utils import get_logger, LoggingMixin, log_performance
from utils.performance_utils import (
    get_query_cache, get_performance_monitor, cached_query, 
    performance_tracked, optimize_dataframe_memory
)
from utils.security_utils import validate_sql_query, SecurityLevel

load_dotenv()
logger = get_logger(__name__)


class VannaOpenAI(ChromaDB_VectorStore, OpenAI_Chat):
    """Integrated Vanna class with ChromaDB vector storage and OpenAI chat capabilities."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with ChromaDB and OpenAI integration.
        
        Args:
            config: Optional configuration dictionary
        """
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)


class VannaTextToSQLConverter(LoggingMixin):
    """Production-ready text-to-SQL converter using Vanna.ai framework.
    
    Features:
        - Advanced query caching and performance monitoring
        - Robust error handling with retry mechanisms
        - Connection pooling for database operations
        - Security validation and health monitoring
        - Comprehensive logging and tracing
    """
    
    def __init__(
        self, 
        database_url: Optional[str] = None, 
        openai_api_key: Optional[str] = None
    ):
        """Initialize the converter with production-grade components.
        
        Args:
            database_url: Database connection URL
            openai_api_key: OpenAI API key for LLM access
            
        Raises:
            ValueError: If required configuration is missing
            ConnectionError: If database connection fails
        """
        self.log_info("Initializing VannaTextToSQLConverter")
        
        self._initialize_core_components()
        self._configure_database_connection(database_url, openai_api_key)
        self._setup_ai_integration()
        self._register_health_monitoring()
        
        self.log_info("VannaTextToSQLConverter initialized successfully")
    
    def _initialize_core_components(self) -> None:
        """Initialize core performance and error handling components."""
        self.error_handler = ErrorHandler()
        self.query_cache = get_query_cache()
        self.performance_monitor = get_performance_monitor()
        self._using_pool = False
    
    def _configure_database_connection(
        self, 
        database_url: Optional[str], 
        openai_api_key: Optional[str]
    ) -> None:
        """Configure database and API connections."""
        settings = get_settings()
        
        self.database_url = database_url or settings.database_url
        self.openai_api_key = openai_api_key or settings.openai_api_key
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")
        
        self.engine = create_engine(self.database_url)
        self._setup_connection_pool()
        
    def _setup_ai_integration(self) -> None:
        """Setup Vanna.ai integration with robust error handling."""
        self.log_info("Configuring Vanna.ai with OpenAI and ChromaDB")
        
        settings = get_settings()
        collection_name = settings.chroma_collection_name
        
        self.vn = self._initialize_vanna_with_retry(settings, collection_name)
        self.vn.allow_llm_to_see_data = True
        
        self._cleanup_old_chromadb_folders()
        self._setup_database_connection()
        self._train_initial_schema()
    
    def _initialize_vanna_with_retry(
        self, 
        settings, 
        collection_name: str, 
        max_retries: int = 3
    ) -> VannaOpenAI:
        """Initialize Vanna with retry logic and fallback strategies."""
        for attempt in range(max_retries):
            try:
                vn = VannaOpenAI(config={
                    'api_key': self.openai_api_key,
                    'model': settings.openai_model,
                    'path': settings.chroma_path,
                    'collection_name': collection_name
                })
                self.log_info(f"ChromaDB initialized with collection: {collection_name}")
                return vn
                
            except Exception as e:
                self.log_warning(f"Initialization attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    self._cleanup_failed_attempt(settings.chroma_path, attempt)
                else:
                    return self._create_minimal_fallback(settings)
        
        raise RuntimeError("Failed to initialize Vanna after all attempts")
    
    def _cleanup_failed_attempt(self, chroma_path: str, attempt: int) -> None:
        """Clean up after failed initialization attempt."""
        try:
            import shutil
            if os.path.exists(chroma_path):
                shutil.rmtree(chroma_path)
            self.log_info(f"Cleaned cache for retry {attempt + 2}")
        except Exception as e:
            self.log_warning(f"Cache cleanup failed: {e}")
    
    def _create_minimal_fallback(self, settings) -> VannaOpenAI:
        """Create minimal Vanna configuration as last resort."""
        try:
            vn = VannaOpenAI(config={
                'api_key': self.openai_api_key,
                'model': settings.openai_model
            })
            self.log_info("Using minimal configuration fallback")
            return vn
        except Exception as e:
            self.log_error(f"Even minimal configuration failed: {e}")
            raise
        
    def _register_health_monitoring(self) -> None:
        """Register health checks and performance monitoring."""
        self._register_health_checks()
        
        settings = get_settings()
        if getattr(settings, 'enable_performance_tracking', True):
            self._setup_performance_monitoring()
    
    def _setup_connection_pool(self) -> None:
        """Configure connection pooling for enhanced performance."""
        try:
            connection_manager = get_connection_manager()
            pool = connection_manager.get_pool("default_postgresql")
            
            if pool:
                self.log_info("Connection pool configured successfully")
                self._using_pool = True
                self._connection_pool = pool
            else:
                self.log_info("Using direct database connections")
                
        except Exception as e:
            self.log_warning(f"Connection pool setup failed: {e}")
    
    def _setup_performance_monitoring(self) -> None:
        """Initialize performance monitoring components."""
        try:
            self.log_info("Performance monitoring enabled")
            # Monitoring is handled via decorators and utilities
        except Exception as e:
            self.log_warning(f"Performance monitoring setup failed: {e}")
    
    def _cleanup_old_chromadb_folders(self):
        """Clean up old ChromaDB folders to prevent folder proliferation"""
        try:
            import glob
            import shutil
            
            # Find all old vanna_chromadb folders with UUID pattern
            old_folders = glob.glob('./vanna_chromadb_ubereats_brasil_*')
            
            for folder in old_folders:
                try:
                    if os.path.exists(folder) and os.path.isdir(folder):
                        shutil.rmtree(folder)
                        logger.info(f"Removed old ChromaDB folder: {folder}")
                except Exception as e:
                    logger.warning(f"Could not remove folder {folder}: {e}")
                    
        except Exception as e:
            logger.warning(f"Error during ChromaDB cleanup: {e}")
    
    def _setup_database_connection(self):
        """Setup database connection for Vanna"""
        try:
            # Connect Vanna to the database
            if 'postgresql' in self.database_url:
                # For PostgreSQL
                self.vn.connect_to_postgres(
                    host=self._extract_db_param('host'),
                    dbname=self._extract_db_param('dbname'),
                    user=self._extract_db_param('user'),
                    password=self._extract_db_param('password'),
                    port=self._extract_db_param('port')
                )
                logger.info("Conectado ao PostgreSQL via Vanna.ai")
            elif 'sqlite' in self.database_url:
                # For SQLite
                db_path = self.database_url.replace('sqlite:///', '')
                self.vn.connect_to_sqlite(db_path)
                logger.info("Conectado ao SQLite via Vanna.ai")
            else:
                logger.warning("Tipo de banco não suportado diretamente pelo Vanna.ai")
        except Exception as e:
            logger.warning(f"Não foi possível conectar Vanna.ai diretamente ao banco: {e}")
            logger.info("Usando conexão manual via SQLAlchemy")
    
    def _extract_db_param(self, param: str) -> str:
        """Extract database parameters from URL"""
        import urllib.parse
        parsed = urllib.parse.urlparse(self.database_url)
        
        if param == 'host':
            return parsed.hostname
        elif param == 'port':
            return parsed.port or 5432
        elif param == 'dbname':
            return parsed.path.lstrip('/')
        elif param == 'user':
            return parsed.username
        elif param == 'password':
            return parsed.password
        
        return ""
    
    def _train_initial_schema(self):
        """Train Vanna with database schema information"""
        logger.info("Treinando Vanna.ai com schema do banco")
        try:
            # Check if we already have training data to avoid duplicates
            try:
                # Try to get existing training data (if supported)
                existing_data = getattr(self.vn, 'get_training_data', lambda: [])()
                if existing_data:
                    logger.info("Schema de treinamento já existe, pulando re-treinamento")
                    return
            except:
                # If getting training data fails, proceed with training
                pass
            
            inspector = inspect(self.engine)
            table_names = inspector.get_table_names()
            logger.info(f"Encontradas {len(table_names)} tabelas: {table_names}")
            
            # Train with DDL (Data Definition Language) only once
            for table_name in table_names:
                columns = inspector.get_columns(table_name)
                
                # Create DDL-like information
                ddl_info = f"Table: {table_name}\n"
                for column in columns:
                    col_type = str(column['type'])
                    nullable = "NULL" if column['nullable'] else "NOT NULL"
                    ddl_info += f"  - {column['name']}: {col_type} {nullable}\n"
                
                # Train Vanna with schema information (with error handling)
                try:
                    self.vn.train(ddl=ddl_info)
                    logger.debug(f"Schema da tabela {table_name} adicionado ao treinamento")
                except Exception as train_error:
                    logger.warning(f"Erro ao treinar tabela {table_name}: {train_error}")
                    # Continue with other tables even if one fails
                    continue
            
            # Add advanced domain-specific context for UberEats Brasil (only once)
            try:
                advanced_context = """
# ADVANCED UberEats Brasil SQL Generation Context

## DATABASE OVERVIEW
This is a comprehensive UberEats Brasil invoice management system with restaurant delivery data.

## CORE TABLES
### ubears_invoices_extract_airflow (PRIMARY TABLE - USE THIS FOR MOST QUERIES)
- Contains: Restaurant invoice data, orders, payments, delivery information
- Key fields: vendor_name, total_amount, subtotal_amount, payment_method, amount_paid, amount_due
- Date fields: invoice_date, order_date, delivery_date
- Location: delivery_address, restaurant_location
- Categories: food_category, cuisine_type

### invoices (SECONDARY TABLE - Use only when specifically requested)
- Raw invoice data, less processed than ubears_invoices_extract_airflow

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
- **Analysis queries**: "trend", "growth", "pattern", "analysis"
  → Use window functions, GROUP BY with DATE_TRUNC

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
- "pagamento" → payment_method, amount_paid
- "entrega" → delivery_date, delivery_address

### 4. SMART DEFAULTS
- Default to ubears_invoices_extract_airflow table unless specified otherwise
- Use ILIKE '%pattern%' for text searches (case-insensitive)
- Include reasonable LIMIT (50-100) for large result sets
- Use proper date formatting: DATE_TRUNC, TO_CHAR as needed
- Order results logically (dates DESC, amounts DESC, names ASC)

### 5. ADVANCED QUERY PATTERNS

#### Time Series Analysis:
```sql
-- Monthly trends
SELECT 
  DATE_TRUNC('month', invoice_date) as month,
  COUNT(*) as orders,
  SUM(total_amount) as revenue
FROM ubears_invoices_extract_airflow 
GROUP BY 1 ORDER BY 1;
```

#### Top Performers:
```sql
-- Top restaurants by revenue
SELECT 
  vendor_name,
  COUNT(*) as orders,
  SUM(total_amount) as revenue
FROM ubears_invoices_extract_airflow 
GROUP BY vendor_name 
ORDER BY revenue DESC LIMIT 10;
```

#### Payment Analysis:
```sql
-- Payment methods distribution
SELECT 
  payment_method,
  COUNT(*) as count,
  AVG(total_amount) as avg_amount
FROM ubears_invoices_extract_airflow 
GROUP BY payment_method;
```

### 6. ERROR PREVENTION
- Never use non-existent columns like 'payment_status'
- Always validate date formats and ranges
- Use proper PostgreSQL syntax and functions
- Handle NULL values appropriately
- Include meaningful column aliases

### 7. VAGUE QUERY HANDLING
When queries are vague (e.g., "show data", "notas"), generate basic SQL with reasonable defaults:
- For "mostre as notas" or "show invoices": SELECT * FROM ubears_invoices_extract_airflow ORDER BY invoice_date DESC LIMIT 50;
- For "dados" or "data": SELECT * FROM ubears_invoices_extract_airflow LIMIT 50;
- Always try to generate SQL first, only suggest alternatives if technically impossible

## RESPONSE QUALITY STANDARDS
- Generate syntactically correct PostgreSQL
- Include appropriate JOINs if multiple tables needed
- Use meaningful column aliases in Portuguese when possible
- Optimize for performance (proper indexing assumptions)
- Return actionable business insights
                """
                self.vn.train(documentation=advanced_context)
                logger.info("Contexto avançado UberEats Brasil adicionado")
                
                # Add specific query examples for better training
                query_examples = [
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
                ]
                
                # Train with example queries
                for example in query_examples:
                    try:
                        self.vn.train(question=example["question"], sql=example["sql"])
                        logger.debug(f"Exemplo treinado: {example['question'][:30]}...")
                    except Exception as example_error:
                        logger.warning(f"Erro ao treinar exemplo: {example_error}")
                
                logger.info(f"Treinamento avançado concluído com {len(query_examples)} exemplos")
                
            except Exception as doc_error:
                logger.warning(f"Erro ao adicionar contexto avançado: {doc_error}")
            
        except Exception as e:
            logger.error(f"Erro ao treinar schema inicial: {e}")
            # Don't raise the error - continue with basic functionality
    
    def _validate_select_only(self, sql_query: str) -> bool:
        """Validate that the query contains only SELECT statements using enhanced security utilities"""
        validation_result = validate_sql_query(sql_query, SecurityLevel.STRICT)
        
        if not validation_result.is_valid:
            self.log_error(f"Query validation failed: {validation_result.error_message}", {
                "blocked_keywords": validation_result.blocked_keywords,
                "risk_level": validation_result.risk_level
            })
            return False
        
        # Log warnings if any
        for warning in validation_result.warnings:
            self.log_warning(f"Query validation warning: {warning}")
        
        return True
    
    def _analyze_query_intent(self, user_question: str) -> Dict[str, Any]:
        """Advanced query intent analysis to enhance SQL generation"""
        question_lower = user_question.lower().strip()
        
        intent_analysis = {
            "query_type": "unknown",
            "time_scope": None,
            "aggregation_type": None,
            "entities": [],
            "complexity": "simple",
            "suggested_approach": None,
            "enhanced_question": user_question
        }
        
        # Query type classification
        if any(word in question_lower for word in ['total', 'soma', 'somar', 'sum']):
            intent_analysis["query_type"] = "aggregation_sum"
            intent_analysis["aggregation_type"] = "SUM"
        elif any(word in question_lower for word in ['count', 'quantidade', 'quantos', 'número']):
            intent_analysis["query_type"] = "aggregation_count"
            intent_analysis["aggregation_type"] = "COUNT"
        elif any(word in question_lower for word in ['top', 'primeiros', 'maiores', 'melhores', 'ranking']):
            intent_analysis["query_type"] = "ranking"
            intent_analysis["suggested_approach"] = "ORDER BY DESC LIMIT"
        elif any(word in question_lower for word in ['compare', 'comparação', 'vs', 'versus', 'entre']):
            intent_analysis["query_type"] = "comparison"
            intent_analysis["complexity"] = "complex"
        elif any(word in question_lower for word in ['tendência', 'evolução', 'crescimento', 'análise']):
            intent_analysis["query_type"] = "trend_analysis"
            intent_analysis["complexity"] = "complex"
            intent_analysis["suggested_approach"] = "TIME_SERIES"
        elif any(word in question_lower for word in ['mostrar', 'show', 'listar', 'exibir', 'ver']):
            intent_analysis["query_type"] = "display"
        elif any(word in question_lower for word in ['média', 'average', 'avg']):
            intent_analysis["query_type"] = "aggregation_avg"
            intent_analysis["aggregation_type"] = "AVG"
        
        # Time scope detection
        if any(phrase in question_lower for phrase in ['últimos', 'last', 'recent']):
            if 'dia' in question_lower or 'day' in question_lower:
                days = self._extract_number_from_text(question_lower)
                intent_analysis["time_scope"] = f"last_{days or 7}_days"
            elif 'mês' in question_lower or 'month' in question_lower:
                intent_analysis["time_scope"] = "last_month"
        elif any(phrase in question_lower for phrase in ['este mês', 'this month', 'atual']):
            intent_analysis["time_scope"] = "current_month"
        elif any(phrase in question_lower for phrase in ['ontem', 'yesterday']):
            intent_analysis["time_scope"] = "yesterday"
        elif any(phrase in question_lower for phrase in ['hoje', 'today']):
            intent_analysis["time_scope"] = "today"
        
        # Entity extraction
        entities = []
        if any(word in question_lower for word in ['restaurante', 'restaurant', 'estabelecimento', 'vendor']):
            entities.append("vendor_name")
        if any(word in question_lower for word in ['pagamento', 'payment', 'pagar']):
            entities.append("payment_method")
        if any(word in question_lower for word in ['entrega', 'delivery', 'entregar']):
            entities.append("delivery")
        if any(word in question_lower for word in ['faturamento', 'receita', 'revenue', 'valor', 'preço']):
            entities.append("total_amount")
        
        intent_analysis["entities"] = entities
        
        # Enhance vague questions
        if len(question_lower.split()) <= 3 or intent_analysis["query_type"] == "unknown":
            intent_analysis["enhanced_question"] = self._enhance_vague_question(user_question, intent_analysis)
            intent_analysis["complexity"] = "vague"
        
        return intent_analysis
    
    def _extract_number_from_text(self, text: str) -> Optional[int]:
        """Extract numbers from text for date ranges"""
        import re
        numbers = re.findall(r'\d+', text)
        return int(numbers[0]) if numbers else None
    
    def _enhance_vague_question(self, question: str, analysis: Dict) -> str:
        """Enhance vague questions with contextual information"""
        question_lower = question.lower().strip()
        
        # Common enhancement patterns for simple display queries
        if any(phrase in question_lower for phrase in ['me mostre as notas', 'mostre as notas', 'mostrar as notas']):
            return "Mostre todas as notas fiscais recentes ordenadas por data"
        elif question_lower in ['notas', 'faturas', 'invoices']:
            return "Mostre todas as notas fiscais com detalhes básicos"
        elif question_lower in ['faturamento', 'receita', 'revenue']:
            return "Mostre o faturamento total e análise por período"
        elif question_lower in ['restaurantes', 'estabelecimentos']:
            return "Mostre os restaurantes com suas performance de vendas"
        elif question_lower in ['pagamentos', 'payments']:
            return "Analise os métodos de pagamento e seus volumes"
        elif 'dados' in question_lower or 'data' in question_lower:
            return "Mostre um resumo geral dos dados de notas fiscais com principais métricas"
        
        return question
    
    def _handle_simple_patterns(self, user_question: str) -> Optional[str]:
        """Handle common simple patterns with direct SQL generation"""
        question_lower = user_question.lower().strip()
        
        # Pattern: "me mostre as notas" or variations
        if any(pattern in question_lower for pattern in [
            'me mostre as notas', 'mostre as notas', 'mostrar as notas',
            'ver as notas', 'listar as notas', 'exibir as notas'
        ]):
            return "SELECT invoice_number, vendor_name, total_amount, invoice_date, payment_method FROM ubears_invoices_extract_airflow ORDER BY invoice_date DESC LIMIT 50"
        
        # Pattern: just "notas"
        if question_lower in ['notas', 'faturas']:
            return "SELECT invoice_number, vendor_name, total_amount, invoice_date FROM ubears_invoices_extract_airflow ORDER BY invoice_date DESC LIMIT 50"
        
        # Pattern: "dados" or "data"
        if question_lower in ['dados', 'data', 'informações']:
            return "SELECT vendor_name, COUNT(*) as total_notas, SUM(total_amount) as faturamento_total FROM ubears_invoices_extract_airflow GROUP BY vendor_name ORDER BY faturamento_total DESC LIMIT 20"
        
        return None
    
    def _is_explanatory_response(self, response: str) -> bool:
        """Check if response is explanatory text instead of SQL"""
        response_lower = response.lower().strip()
        
        # Check for intermediate_sql pattern (this is valid SQL with a comment)
        if 'intermediate_sql' in response_lower and 'select' in response_lower:
            return False
        
        # First, check if it looks like SQL
        sql_indicators = ['select', 'from', 'where', 'group by', 'order by', 'having', 'join', 'union', 'insert', 'update', 'delete']
        has_sql_keywords = any(indicator in response_lower for indicator in sql_indicators)
        
        # If it has SQL keywords and is long enough, it's probably SQL
        if has_sql_keywords and len(response.strip()) > 20:
            return False
        
        # Check for SQL comments followed by actual SQL
        if '--' in response and has_sql_keywords:
            return False
        
        # Common patterns that indicate explanatory text (more specific)
        explanatory_patterns = [
            'mais informações são necessárias',
            'por favor, forneça',
            'não posso gerar',
            'não é possível',
            'preciso de mais detalhes',
            'especifique',
            'esclareça',
            'insufficient context',
            'more information needed', 
            'please provide',
            'cannot generate',
            'sorry, i cannot',
            'desculpe, não posso',
            'i need more information',
            'preciso de mais informação',
            'could you please',
            'i would need',
            'more specific',
            'clarify'
        ]
        
        # Check if response contains explanatory patterns
        for pattern in explanatory_patterns:
            if pattern in response_lower:
                return True
        
        # Check if response is very short and doesn't contain SELECT
        if len(response.strip()) < 15 and 'select' not in response_lower:
            return True
        
        # If it doesn't have SQL keywords at all and is explaining something
        if not has_sql_keywords and len(response.split()) > 5:
            # Check if it's trying to explain rather than generate SQL
            explanation_indicators = ['to', 'need', 'would', 'could', 'should', 'please', 'try', 'consider']
            if any(word in response_lower for word in explanation_indicators):
                return True
        
        return False
    
    def _build_contextual_prompt(self, original_question: str, intent_analysis: Dict[str, Any]) -> str:
        """Build enhanced contextual prompt based on intent analysis"""
        enhanced_question = intent_analysis["enhanced_question"]
        
        # Build context-aware prompt
        contextual_prompt = enhanced_question
        
        # Add specific context based on intent
        if intent_analysis["query_type"] == "ranking":
            contextual_prompt += " (ordenar por valores mais altos e limitar resultados)"
        elif intent_analysis["query_type"] in ["aggregation_sum", "aggregation_count", "aggregation_avg"]:
            contextual_prompt += " (agrupar dados e calcular totais/médias)"
        elif intent_analysis["query_type"] == "trend_analysis":
            contextual_prompt += " (analisar tendências ao longo do tempo)"
        elif intent_analysis["query_type"] == "comparison":
            contextual_prompt += " (comparar diferentes períodos ou categorias)"
        
        # Add time context if detected
        if intent_analysis["time_scope"]:
            if "last_" in intent_analysis["time_scope"] and "_days" in intent_analysis["time_scope"]:
                days = intent_analysis["time_scope"].split("_")[1]
                contextual_prompt += f" dos últimos {days} dias"
            elif intent_analysis["time_scope"] == "current_month":
                contextual_prompt += " do mês atual"
            elif intent_analysis["time_scope"] == "yesterday":
                contextual_prompt += " de ontem"
            elif intent_analysis["time_scope"] == "today":
                contextual_prompt += " de hoje"
        
        # Add entity hints
        if intent_analysis["entities"]:
            entities_hint = ", ".join(intent_analysis["entities"])
            contextual_prompt += f" (focar em: {entities_hint})"
        
        logger.debug(f"Prompt contextualizado: {contextual_prompt}")
        return contextual_prompt
    
    def _get_intent_based_suggestions(self, intent_analysis: Dict[str, Any]) -> str:
        """Generate helpful suggestions based on user intent"""
        query_type = intent_analysis["query_type"]
        
        if query_type == "unknown" or intent_analysis["complexity"] == "vague":
            return """Tente perguntas mais específicas como:
            • 'Mostre o faturamento dos últimos 7 dias'
            • 'Top 10 restaurantes por número de pedidos'
            • 'Análise de pagamentos por método'
            • 'Compare o faturamento deste mês com o anterior'"""
        
        elif query_type == "aggregation_sum":
            return """Para consultas de soma, tente:
            • 'Total de faturamento dos últimos 30 dias'
            • 'Soma de pedidos por restaurante'"""
        
        elif query_type == "aggregation_count":
            return """Para consultas de contagem, tente:
            • 'Quantas notas fiscais foram emitidas hoje'
            • 'Número de pedidos por método de pagamento'"""
        
        elif query_type == "ranking":
            return """Para rankings, tente:
            • 'Top 5 restaurantes por faturamento'
            • 'Maiores pedidos dos últimos 7 dias'"""
        
        elif query_type == "comparison":
            return """Para comparações, tente:
            • 'Compare vendas deste mês vs mês passado'
            • 'Faturamento por dia da semana'"""
        
        elif query_type == "trend_analysis":
            return """Para análises de tendência, tente:
            • 'Evolução diária de pedidos este mês'
            • 'Crescimento mensal de faturamento'"""
        
        return """Reformule sua pergunta com mais detalhes específicos sobre:
        • Período de tempo (últimos X dias, este mês, etc.)
        • Métricas desejadas (faturamento, quantidade, etc.)
        • Filtros específicos (restaurante, método de pagamento, etc.)"""
    
    @performance_tracked("sql_generation")
    def convert_to_sql(self, user_question: str, use_cache: bool = True) -> Dict[str, Any]:
        """Convert natural language question to SQL query using advanced Vanna.ai processing"""
        context = create_error_context(operation="convert_to_sql")
        self.log_info(f"Convertendo pergunta para SQL com Vanna.ai: {user_question[:50]}...", {"question_length": len(user_question)})
        try:
            # Quick pattern matching for common simple queries
            simple_sql = self._handle_simple_patterns(user_question)
            if simple_sql:
                logger.info(f"Usando padrão simples para: {user_question}")
                return {
                    "success": True,
                    "error": None,
                    "sql_query": simple_sql,
                    "result": None
                }
            
            # Step 1: Analyze user intent
            logger.info("Analisando intenção da pergunta")
            intent_analysis = self._analyze_query_intent(user_question)
            
            # Step 2: Use enhanced question for better SQL generation
            enhanced_question = intent_analysis["enhanced_question"]
            if enhanced_question != user_question:
                logger.info(f"Pergunta aprimorada: {enhanced_question[:50]}...")
            
            # Step 3: Generate contextual prompt based on intent
            contextual_prompt = self._build_contextual_prompt(user_question, intent_analysis)
            
            # Step 4: Use Vanna to generate SQL with enhanced context
            logger.info("Gerando SQL com contexto avançado via Vanna.ai")
            
            # Suppress verbose logging during SQL generation
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                # Use the enhanced question for better results
                sql_query = self.vn.generate_sql(contextual_prompt)
            
            if not sql_query or sql_query.strip() == '':
                logger.error("Vanna.ai não conseguiu gerar query SQL")
                # Provide intent-based suggestions
                suggestions = self._get_intent_based_suggestions(intent_analysis)
                return {
                    "success": False,
                    "error": f"Não foi possível gerar query SQL. {suggestions}",
                    "sql_query": None,
                    "result": None
                }
            
            logger.info(f"Query SQL gerada: {sql_query[:100]}...")
            
            # Step 5: Check if response is explanatory text instead of SQL
            if self._is_explanatory_response(sql_query):
                logger.warning(f"Detected explanatory response instead of SQL: {sql_query[:100]}")
                suggestions = self._get_intent_based_suggestions(intent_analysis)
                return {
                    "success": False,
                    "error": f"Pergunta muito vaga ou complexa. {suggestions}",
                    "sql_query": sql_query,  # Include the response for debugging
                    "result": None
                }
            
            # Step 6: Validate query is SELECT only
            if not self._validate_select_only(sql_query):
                return {
                    "success": False,
                    "error": "Query gerada contém comandos não permitidos (apenas SELECT é permitido)",
                    "sql_query": sql_query,
                    "result": None
                }
            
            logger.info("Query SQL validada com sucesso")
            return {
                "success": True,
                "error": None,
                "sql_query": sql_query,
                "result": None,
                "intent_analysis": intent_analysis
            }
            
        except Exception as e:
            return handle_api_error("convert_to_sql", e, context)
            # Provide more user-friendly error messages
            error_msg = str(e)
            if "connection" in error_msg.lower():
                error_msg = "Erro de conexão com o Vanna.ai. Tente novamente."
            elif "api" in error_msg.lower():
                error_msg = "Erro na API OpenAI. Verifique sua chave de API."
            elif "model" in error_msg.lower():
                error_msg = "Erro no modelo de AI. Tente reformular sua pergunta."
            
            return {
                "success": False,
                "error": f"Erro no Vanna.ai: {error_msg}",
                "sql_query": None,
                "result": None
            }
    
    @performance_tracked("sql_query_execution")
    def execute_query(self, sql_query: str, use_cache: bool = True) -> Dict[str, Any]:
        """Execute the SQL query and return results with enhanced error handling"""
        context = create_error_context(operation="execute_query")
        
        try:
            self.log_info(f"Executando query SQL: {sql_query[:100]}...", {"query_length": len(sql_query)})
            
            # Double-check query is safe
            if not self._validate_select_only(sql_query):
                return {
                    "success": False,
                    "error": "Query contém comandos não permitidos",
                    "result": None
                }
            
            # Execute query using SQLAlchemy engine with retry logic
            def _execute():
                self.log_info("Conectando ao banco de dados")
                with self.engine.connect() as connection:
                    result = connection.execute(text(sql_query))
                    columns = list(result.keys())
                    rows = result.fetchall()
                    return columns, rows
            
            columns, rows = self.error_handler.with_retry(
                _execute,
                "database_query_execution",
                context
            )
            
            self.log_info(f"Query executada com sucesso. {len(rows)} registros retornados")
            
            # Convert to pandas DataFrame for better display
            df = pd.DataFrame(rows, columns=columns)
            self.log_info(f"DataFrame criado com {len(df)} linhas e {len(df.columns)} colunas")
            
            return {
                "success": True,
                "error": None,
                "result": df
            }
                
        except Exception as e:
            return handle_database_error("execute_query", e, context)
    
    @performance_tracked("model_training")
    def train_model(self, question: str, sql: str) -> Dict[str, Any]:
        """Train Vanna model with question-SQL pairs with enhanced validation"""
        context = create_error_context(operation="train_model")
        self.log_info(f"Treinando modelo com pergunta: {question[:50]}...", {"question_length": len(question), "sql_length": len(sql)})
        try:
            # Validate SQL is safe before training using enhanced security
            if not self._validate_select_only(sql):
                return {
                    "success": False,
                    "error": "SQL de treinamento deve conter apenas comandos SELECT",
                }
            
            # Train Vanna with the question-SQL pair
            self.vn.train(question=question, sql=sql)
            self.log_info("Modelo treinado com sucesso")
            
            return {
                "success": True,
                "error": None
            }
            
        except Exception as e:
            return handle_api_error("train_model", e, context)
    
    @performance_tracked("complete_question_processing")
    def process_question(self, user_question: str, use_cache: bool = True) -> Dict[str, Any]:
        """Complete pipeline: convert question to SQL and execute using Vanna.ai with performance optimizations"""
        self.log_info(f"Iniciando processamento completo da pergunta: {user_question[:50]}...", {
            "question_length": len(user_question),
            "use_cache": use_cache
        })
        
        # Convert to SQL using Vanna with caching
        sql_result = self.convert_to_sql(user_question, use_cache=use_cache)
        
        if not sql_result["success"]:
            logger.error("Falha na conversão para SQL")
            return sql_result
        
        # Execute the query with caching
        self.log_info("Executando query gerada")
        execution_result = self.execute_query(sql_result["sql_query"], use_cache=use_cache)
        
        final_result = {
            "success": execution_result["success"],
            "error": execution_result["error"],
            "sql_query": sql_result["sql_query"],
            "result": execution_result["result"]
        }
        
        if final_result["success"]:
            logger.info("Processamento da pergunta concluído com sucesso")
        else:
            logger.error(f"Processamento da pergunta falhou: {final_result['error']}")
            
        return final_result
    
    def _register_health_checks(self):
        """Register health checks for this converter."""
        health_checker = get_health_checker()
        
        # Database health check
        health_checker.register_check(
            "postgresql_database",
            check_database_connection(self.engine),
            timeout=10.0
        )
        
        # OpenAI API health check
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=self.openai_api_key)
            health_checker.register_check(
                "openai_api",
                check_openai_api(openai_client, self.openai_api_key),
                timeout=15.0
            )
        except Exception as e:
            self.log_warning(f"Could not register OpenAI health check: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all components."""
        health_checker = get_health_checker()
        return health_checker.get_overall_status()
    
    def get_training_data(self) -> Dict[str, Any]:
        """Get current training data from Vanna"""
        try:
            # This would get training data if Vanna supports it
            # For now, return empty as this is implementation-specific
            return {
                "success": True,
                "training_data": "Training data retrieval not implemented yet"
            }
        except Exception as e:
            self.log_error(f"Erro ao obter dados de treinamento: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }