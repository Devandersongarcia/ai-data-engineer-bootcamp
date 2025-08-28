"""Enhanced Vanna converter with configurable table support and zero-downtime migration capability."""

import re
import logging
import os
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, inspect, text
import pandas as pd
from dotenv import load_dotenv

# Disable telemetry
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['POSTHOG_DISABLE'] = 'true'

# Vanna.ai imports
from vanna.chromadb.chromadb_vector import ChromaDB_VectorStore
from vanna.openai.openai_chat import OpenAI_Chat

# Configuration imports
from config.settings import get_settings
from config.table_configs import (
    get_table_config_manager, get_table_config, 
    TableConfiguration, TableConfigurationManager
)

# Utility imports
from utils.logging_utils import get_logger, LoggingMixin, log_performance
from utils.security_utils import validate_sql_query, SecurityLevel
from utils.error_handling import handle_database_error, handle_api_error, create_error_context, ErrorHandler
from utils.health_check import get_health_checker, check_database_connection, check_openai_api
from utils.performance_utils import get_query_cache, get_performance_monitor, cached_query, performance_tracked, optimize_dataframe_memory
from utils.connection_pool import get_connection_manager
from utils.async_utils import make_async_compatible
import time

load_dotenv()

# Configure logging using enhanced utilities
logger = get_logger(__name__)


class VannaOpenAI(ChromaDB_VectorStore, OpenAI_Chat):
    """Custom Vanna class combining ChromaDB vector store with OpenAI chat"""
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)


class EnhancedVannaTextToSQLConverter(LoggingMixin):
    """
    Enhanced Text to SQL converter with configurable table support.
    
    Maintains 100% backward compatibility while adding support for multiple table configurations.
    Supports zero-downtime migration between different database schemas.
    """
    
    def __init__(
        self, 
        database_url: Optional[str] = None, 
        openai_api_key: Optional[str] = None,
        primary_table: Optional[str] = None,
        auto_detect_schema: bool = True
    ):
        """
        Initialize the enhanced converter.
        
        Args:
            database_url: Database connection URL
            openai_api_key: OpenAI API key
            primary_table: Primary table to use (None = use default for backward compatibility)
            auto_detect_schema: Whether to automatically detect and configure schema
        """
        self.log_info("Inicializando EnhancedVannaTextToSQLConverter")
        
        # Initialize configuration manager
        self.config_manager = get_table_config_manager()
        
        # Determine primary table (backward compatibility)
        if primary_table is None:
            # Default to invoices for backward compatibility
            self.primary_table = "ubears_invoices_extract_airflow"
            self.log_info("Using default table for backward compatibility")
        else:
            self.primary_table = primary_table
            # Set new default for future operations
            try:
                self.config_manager.set_default_table(primary_table)
                self.log_info(f"Switched to primary table: {primary_table}")
            except ValueError as e:
                self.log_warning(f"Could not set primary table {primary_table}: {e}")
                self.primary_table = "ubears_invoices_extract_airflow"
        
        # Get table configuration
        self.table_config = get_table_config(self.primary_table)
        self.log_info(f"Loaded configuration for table: {self.table_config.table_name}")
        
        # Initialize error handler and performance components
        self.error_handler = ErrorHandler()
        self.query_cache = get_query_cache()
        self.performance_monitor = get_performance_monitor()
        self._using_pool = False
        
        # Get settings with fallbacks
        settings = get_settings()
        self.database_url = database_url or settings.database_url
        self.openai_api_key = openai_api_key or settings.openai_api_key
        
        # Initialize database engine
        self.engine = create_engine(self.database_url)
        
        # Setup connection pool
        self._setup_connection_pool()
        
        if not self.openai_api_key:
            self.log_error("Chave da API OpenAI não fornecida")
            raise ValueError("OpenAI API key is required")
        
        # Initialize Vanna with table-specific configuration
        self._setup_vanna()
        
        # Setup database connection and training
        if auto_detect_schema:
            self._setup_database_and_training()
        
        # Register health checks and performance monitoring
        self._register_health_checks()
        settings = get_settings()
        if settings.enable_performance_tracking:
            self._setup_performance_monitoring()
    
    def _setup_vanna(self):
        """Setup Vanna with table-specific configuration."""
        self.log_info("Configurando Vanna.ai com configuração específica da tabela")
        
        # Use table-specific collection name to avoid conflicts
        collection_name = f"ubereats_brasil_{self.table_config.table_type.value}"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                settings = get_settings()
                chroma_path = f"{settings.chroma_path}_{self.table_config.table_type.value}"
                
                self.vn = VannaOpenAI(config={
                    'api_key': self.openai_api_key,
                    'model': settings.openai_model,
                    'path': chroma_path,
                    'collection_name': collection_name
                })
                self.log_info(f"ChromaDB inicializado com collection: {collection_name}")
                break
                
            except Exception as e:
                self.log_warning(f"Tentativa {attempt + 1} falhou: {e}", {"attempt": attempt + 1})
                
                if attempt < max_retries - 1:
                    # Clean up and retry
                    try:
                        import shutil
                        if os.path.exists(chroma_path):
                            shutil.rmtree(chroma_path)
                        self.log_info(f"Cache limpo para tentativa {attempt + 2}")
                    except Exception as cleanup_error:
                        self.log_warning(f"Erro ao limpar cache: {cleanup_error}")
                else:
                    # Final fallback
                    self.log_info("Usando configuração mínima como último recurso...")
                    try:
                        settings = get_settings()
                        self.vn = VannaOpenAI(config={
                            'api_key': self.openai_api_key,
                            'model': settings.openai_model
                        })
                        self.log_info("Configuração mínima bem-sucedida")
                    except Exception as final_error:
                        self.log_error(f"Todas as tentativas falharam: {final_error}")
                        raise final_error
    
    def _setup_connection_pool(self):
        """Setup connection pool for better performance."""
        try:
            connection_manager = get_connection_manager()
            pool = connection_manager.get_pool("default_postgresql")
            
            if pool:
                self.log_info("Using connection pool for database operations")
                self._using_pool = True
                self._connection_pool = pool
            else:
                self.log_info("Connection pool not available, using direct connection")
                
        except Exception as e:
            self.log_warning(f"Could not setup connection pool: {e}")
    
    def _setup_performance_monitoring(self):
        """Setup performance monitoring for the converter."""
        try:
            self.log_info("Performance monitoring enabled")
        except Exception as e:
            self.log_warning(f"Could not setup performance monitoring: {e}")
    
    def _setup_database_and_training(self):
        """Setup database connection and train with table-specific schema."""
        self.log_info("Configurando conexão do banco e treinamento específico da tabela")
        
        # Setup database connection
        self._setup_database_connection()
        
        # Train with table-specific schema and examples
        self._train_table_specific_schema()
    
    def _setup_database_connection(self):
        """Setup database connection for Vanna."""
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
        """Extract database parameters from URL."""
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
    
    def _train_table_specific_schema(self):
        """Train Vanna with table-specific schema and examples."""
        logger.info(f"Treinando Vanna.ai com schema da tabela: {self.table_config.table_name}")
        
        try:
            # Check if we already have training data to avoid duplicates
            try:
                existing_data = getattr(self.vn, 'get_training_data', lambda: [])()
                if existing_data:
                    logger.info("Schema de treinamento já existe, verificando se precisa de atualização")
            except:
                pass
            
            # Train with actual database schema
            self._train_database_schema()
            
            # Train with table-specific advanced context
            self._train_advanced_context()
            
            # Train with table-specific examples
            self._train_example_queries()
            
            logger.info("Treinamento específico da tabela concluído")
            
        except Exception as e:
            logger.error(f"Erro ao treinar schema específico da tabela: {e}")
    
    def _train_database_schema(self):
        """Train with actual database schema for the configured table."""
        inspector = inspect(self.engine)
        
        # Verify the configured table exists
        table_names = inspector.get_table_names()
        if self.table_config.table_name not in table_names:
            raise ValueError(f"Configured table '{self.table_config.table_name}' not found in database")
        
        logger.info(f"Treinando schema para tabela: {self.table_config.table_name}")
        
        # Get table schema
        columns = inspector.get_columns(self.table_config.table_name)
        
        # Create comprehensive DDL information
        ddl_info = f"Table: {self.table_config.table_name} ({self.table_config.table_type.value})\n"
        for column in columns:
            col_type = str(column['type'])
            nullable = "NULL" if column['nullable'] else "NOT NULL"
            ddl_info += f"  - {column['name']}: {col_type} {nullable}\n"
        
        # Add business context from configuration
        ddl_info += f"\nBusiness Context:\n"
        for field_group in [
            self.table_config.primary_fields,
            self.table_config.date_fields,
            self.table_config.amount_fields,
            self.table_config.status_fields,
            self.table_config.relationship_fields
        ]:
            for field in field_group:
                ddl_info += f"  - {field.db_field}: {field.description} ({field.business_concept})\n"
        
        # Train Vanna with enhanced schema information
        try:
            self.vn.train(ddl=ddl_info)
            logger.info(f"Schema da tabela {self.table_config.table_name} treinado com sucesso")
        except Exception as train_error:
            logger.warning(f"Erro ao treinar schema da tabela: {train_error}")
        
        # Also train related tables for JOIN capabilities
        self._train_related_tables_schema(inspector, table_names)
    
    def _train_related_tables_schema(self, inspector, available_tables: List[str]):
        """Train schema for related tables to enable JOIN queries."""
        # Define potential related tables based on the primary table
        if self.table_config.table_name == "payments":
            related_tables = ["orders", "users", "drivers"]
        elif self.table_config.table_name == "ubears_invoices_extract_airflow":
            related_tables = ["invoices", "payments", "orders"]
        else:
            related_tables = []
        
        for related_table in related_tables:
            if related_table in available_tables:
                try:
                    columns = inspector.get_columns(related_table)
                    ddl_info = f"Related Table: {related_table}\n"
                    for column in columns[:10]:  # Limit to first 10 columns for related tables
                        col_type = str(column['type'])
                        nullable = "NULL" if column['nullable'] else "NOT NULL"
                        ddl_info += f"  - {column['name']}: {col_type} {nullable}\n"
                    
                    self.vn.train(ddl=ddl_info)
                    logger.debug(f"Schema da tabela relacionada {related_table} treinado")
                except Exception as e:
                    logger.warning(f"Erro ao treinar tabela relacionada {related_table}: {e}")
    
    def _train_advanced_context(self):
        """Train with table-specific advanced context."""
        try:
            self.vn.train(documentation=self.table_config.advanced_context)
            logger.info("Contexto avançado específico da tabela adicionado")
        except Exception as doc_error:
            logger.warning(f"Erro ao adicionar contexto avançado: {doc_error}")
    
    def _train_example_queries(self):
        """Train with table-specific example queries."""
        try:
            for example in self.table_config.training_examples:
                try:
                    self.vn.train(question=example["question"], sql=example["sql"])
                    logger.debug(f"Exemplo treinado: {example['question'][:30]}...")
                except Exception as example_error:
                    logger.warning(f"Erro ao treinar exemplo: {example_error}")
            
            logger.info(f"Treinamento concluído com {len(self.table_config.training_examples)} exemplos")
        except Exception as e:
            logger.warning(f"Erro no treinamento de exemplos: {e}")
    
    def _validate_select_only(self, sql_query: str) -> bool:
        """Validate that the query contains only SELECT statements."""
        validation_result = validate_sql_query(sql_query, SecurityLevel.STRICT)
        
        if not validation_result.is_valid:
            self.log_error(f"Query validation failed: {validation_result.error_message}", {
                "blocked_keywords": validation_result.blocked_keywords,
                "risk_level": validation_result.risk_level
            })
            return False
        
        for warning in validation_result.warnings:
            self.log_warning(f"Query validation warning: {warning}")
        
        return True
    
    def _handle_simple_patterns(self, user_question: str) -> Optional[str]:
        """Handle simple patterns using table-specific configuration."""
        question_lower = user_question.lower().strip()
        
        # Check table-specific simple patterns first
        for pattern, sql in self.table_config.simple_patterns.items():
            if pattern in question_lower:
                self.log_info(f"Using simple pattern for: {pattern}")
                return sql
        
        return None
    
    def _enhance_question_with_context(self, user_question: str) -> str:
        """Enhance user question with table-specific context."""
        question_lower = user_question.lower()
        enhanced_question = user_question
        
        # Apply Portuguese mappings from table configuration
        for portuguese_term, sql_concept in self.table_config.portuguese_mappings.items():
            if portuguese_term in question_lower:
                # Add context hint based on the mapping
                if sql_concept.startswith("SELECT") or sql_concept.startswith("COUNT"):
                    enhanced_question += f" (usar {sql_concept})"
                else:
                    enhanced_question += f" (campo: {sql_concept})"
                break
        
        return enhanced_question
    
    @performance_tracked("sql_generation")
    def convert_to_sql(self, user_question: str, use_cache: bool = True) -> Dict[str, Any]:
        """Convert natural language question to SQL using table-specific configuration."""
        context = create_error_context(operation="convert_to_sql")
        self.log_info(f"Convertendo pergunta para SQL: {user_question[:50]}...", {
            "question_length": len(user_question),
            "primary_table": self.primary_table
        })
        
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
            
            # Enhance question with table-specific context
            enhanced_question = self._enhance_question_with_context(user_question)
            if enhanced_question != user_question:
                logger.info(f"Pergunta aprimorada: {enhanced_question[:50]}...")
            
            # Generate SQL with Vanna
            logger.info("Gerando SQL com Vanna.ai usando configuração específica da tabela")
            
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                sql_query = self.vn.generate_sql(enhanced_question)
            
            if not sql_query or sql_query.strip() == '':
                logger.error("Vanna.ai não conseguiu gerar query SQL")
                return {
                    "success": False,
                    "error": "Não foi possível gerar query SQL. Tente reformular sua pergunta.",
                    "sql_query": None,
                    "result": None
                }
            
            logger.info(f"Query SQL gerada: {sql_query[:100]}...")
            
            # Validate query
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
                "table_config": self.table_config.table_name
            }
            
        except Exception as e:
            return handle_api_error("convert_to_sql", e, context)
    
    @performance_tracked("sql_query_execution")
    def execute_query(self, sql_query: str, use_cache: bool = True) -> Dict[str, Any]:
        """Execute the SQL query and return results."""
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
            
            # Execute query
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
            
            # Convert to pandas DataFrame
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
        """Train Vanna model with question-SQL pairs."""
        context = create_error_context(operation="train_model")
        self.log_info(f"Treinando modelo: {question[:50]}...", {
            "question_length": len(question), 
            "sql_length": len(sql),
            "table": self.primary_table
        })
        
        try:
            # Validate SQL is safe
            if not self._validate_select_only(sql):
                return {
                    "success": False,
                    "error": "SQL de treinamento deve conter apenas comandos SELECT",
                }
            
            # Train Vanna
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
        """Complete pipeline: convert question to SQL and execute."""
        self.log_info(f"Processamento completo: {user_question[:50]}...", {
            "question_length": len(user_question),
            "use_cache": use_cache,
            "table": self.primary_table
        })
        
        # Convert to SQL
        sql_result = self.convert_to_sql(user_question, use_cache=use_cache)
        
        if not sql_result["success"]:
            logger.error("Falha na conversão para SQL")
            return sql_result
        
        # Execute query
        self.log_info("Executando query gerada")
        execution_result = self.execute_query(sql_result["sql_query"], use_cache=use_cache)
        
        final_result = {
            "success": execution_result["success"],
            "error": execution_result["error"],
            "sql_query": sql_result["sql_query"],
            "result": execution_result["result"],
            "table_used": self.table_config.table_name,
            "table_type": self.table_config.table_type.value
        }
        
        if final_result["success"]:
            logger.info("Processamento concluído com sucesso")
        else:
            logger.error(f"Processamento falhou: {final_result['error']}")
            
        return final_result
    
    def switch_table(self, table_name: str, retrain: bool = True) -> Dict[str, Any]:
        """
        Switch to a different primary table configuration.
        Useful for runtime table switching without restart.
        """
        try:
            self.log_info(f"Switching from {self.primary_table} to {table_name}")
            
            # Get new configuration
            new_config = get_table_config(table_name)
            
            # Update instance configuration
            old_table = self.primary_table
            self.primary_table = table_name
            self.table_config = new_config
            
            # Reinitialize Vanna with new configuration if requested
            if retrain:
                self._setup_vanna()
                self._train_table_specific_schema()
                self.log_info(f"Retraining completed for {table_name}")
            
            self.log_info(f"Successfully switched from {old_table} to {table_name}")
            
            return {
                "success": True,
                "message": f"Switched to table: {table_name}",
                "old_table": old_table,
                "new_table": table_name
            }
            
        except Exception as e:
            self.log_error(f"Failed to switch table: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_table_info(self) -> Dict[str, Any]:
        """Get information about current table configuration."""
        return {
            "primary_table": self.primary_table,
            "table_type": self.table_config.table_type.value,
            "supported_tables": self.config_manager.get_available_tables(),
            "field_mappings": len(self.table_config.portuguese_mappings),
            "training_examples": len(self.table_config.training_examples)
        }
    
    def _register_health_checks(self):
        """Register health checks."""
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
        status = health_checker.get_overall_status()
        status["table_config"] = self.get_table_info()
        return status


# Backward compatibility alias
VannaTextToSQLConverter = EnhancedVannaTextToSQLConverter


def create_payments_converter(database_url: Optional[str] = None, openai_api_key: Optional[str] = None) -> EnhancedVannaTextToSQLConverter:
    """Create a converter configured for payments table."""
    return EnhancedVannaTextToSQLConverter(
        database_url=database_url,
        openai_api_key=openai_api_key,
        primary_table="payments"
    )


def create_invoices_converter(database_url: Optional[str] = None, openai_api_key: Optional[str] = None) -> EnhancedVannaTextToSQLConverter:
    """Create a converter configured for invoices table (backward compatibility)."""
    return EnhancedVannaTextToSQLConverter(
        database_url=database_url,
        openai_api_key=openai_api_key,
        primary_table="ubears_invoices_extract_airflow"
    )