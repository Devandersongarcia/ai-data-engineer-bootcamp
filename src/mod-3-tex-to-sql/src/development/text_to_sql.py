import re
import logging
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from sqlalchemy import create_engine, inspect, MetaData, text
import pandas as pd
import os
from dotenv import load_dotenv

# Import new core functionality
from core.langfuse_service import LangfuseService, get_fallback_prompt
from config.settings import get_dev_settings

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class TextToSQLConverter:
    def __init__(self, database_url: str, openai_api_key: Optional[str] = None):
        logger.info("Inicializando TextToSQLConverter")
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.openai_api_key:
            logger.error("Chave da API OpenAI não fornecida")
            raise ValueError("OpenAI API key is required")
        
        logger.info("Configurando modelo LLM")
        self.llm = ChatOpenAI(
            openai_api_key=self.openai_api_key,
            model="gpt-3.5-turbo",
            temperature=0
        )
        
        # Initialize Langfuse service with fallback configuration
        logger.info("Inicializando serviço Langfuse")
        try:
            settings = get_dev_settings()
            self.langfuse_service = LangfuseService(settings)
        except Exception as e:
            logger.warning(f"Falha ao inicializar Langfuse, usando fallback: {e}")
            self.langfuse_service = None
        
        logger.info("Carregando schema do banco de dados")
        self.schema_info = self._get_database_schema()
        logger.info(f"Schema carregado com {len(self.schema_info.split('Table:'))-1} tabelas")
    
    def _get_database_schema(self) -> str:
        """Get database schema information for context"""
        logger.info("Extraindo informações do schema do banco")
        inspector = inspect(self.engine)
        schema_info = []
        
        table_names = inspector.get_table_names()
        logger.info(f"Encontradas {len(table_names)} tabelas: {table_names}")
        
        for table_name in table_names:
            schema_info.append(f"\nTable: {table_name}")
            columns = inspector.get_columns(table_name)
            logger.debug(f"Tabela {table_name} tem {len(columns)} colunas")
            for column in columns:
                col_type = str(column['type'])
                nullable = "NULL" if column['nullable'] else "NOT NULL"
                schema_info.append(f"  - {column['name']}: {col_type} {nullable}")
        
        return "\n".join(schema_info)
    
    def _validate_select_only(self, sql_query: str) -> bool:
        """Validate that the query contains only SELECT statements"""
        sql_normalized = re.sub(r'\s+', ' ', sql_query.strip().upper())
        
        # Remove comments
        sql_normalized = re.sub(r'--.*$', '', sql_normalized, flags=re.MULTILINE)
        sql_normalized = re.sub(r'/\*.*?\*/', '', sql_normalized, flags=re.DOTALL)
        
        # Check for dangerous keywords using word boundaries
        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
            'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE'
        ]
        
        for keyword in dangerous_keywords:
            # Use word boundaries to avoid false positives like 'INTERVAL' containing 'CREATE'
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_normalized):
                return False
        
        # Must start with SELECT
        return sql_normalized.strip().startswith('SELECT')
    
    def _extract_token_usage(self, response) -> Optional[Dict[str, int]]:
        """Extract token usage from LLM response."""
        try:
            # For OpenAI responses - usage_metadata is a dict
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                return {
                    "input_tokens": usage.get('input_tokens', 0),
                    "output_tokens": usage.get('output_tokens', 0),
                    "total_tokens": usage.get('total_tokens', 0)
                }
            elif hasattr(response, 'response_metadata'):
                usage = response.response_metadata.get('token_usage', {})
                return {
                    "input_tokens": usage.get('prompt_tokens', 0),
                    "output_tokens": usage.get('completion_tokens', 0),
                    "total_tokens": usage.get('total_tokens', 0)
                }
        except Exception as e:
            logger.debug(f"Could not extract token usage: {e}")
            
        return None
    
    def _calculate_cost(self, token_usage: Dict[str, int], model: str = "gpt-3.5-turbo") -> Optional[float]:
        """Calculate estimated cost based on token usage."""
        if not token_usage:
            return None
            
        # Pricing as of 2024 (update as needed)
        pricing = {
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},  # per 1K tokens
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03}
        }
        
        if model not in pricing:
            model = "gpt-3.5-turbo"  # default
            
        try:
            input_cost = (token_usage.get('input_tokens', 0) / 1000) * pricing[model]['input']
            output_cost = (token_usage.get('output_tokens', 0) / 1000) * pricing[model]['output']
            return input_cost + output_cost
        except Exception as e:
            logger.debug(f"Could not calculate cost: {e}")
            return None
    
    def _fix_duplicate_columns(self, sql_query: str) -> str:
        """Fix SQL queries with duplicate column patterns like 'SELECT column, * FROM table'."""
        try:
            # Pattern: SELECT column_name, * FROM table
            # Fix: Change to SELECT * FROM table (since * includes all columns)
            pattern = r'SELECT\s+(\w+(?:\s*,\s*\w+)*)\s*,\s*\*\s+FROM'
            
            if re.search(pattern, sql_query, re.IGNORECASE):
                logger.info(f"Fixing duplicate column pattern in: {sql_query[:50]}...")
                # Replace with SELECT * FROM
                fixed_query = re.sub(pattern, 'SELECT * FROM', sql_query, flags=re.IGNORECASE)
                logger.info(f"Fixed to: {fixed_query[:50]}...")
                return fixed_query
            
            return sql_query
            
        except Exception as e:
            logger.debug(f"Error fixing duplicate columns: {e}")
            return sql_query
    
    def _create_sql_prompt(self, user_question: str) -> str:
        """Create a prompt for SQL generation using Langfuse or fallback"""
        # Try to get prompt from Langfuse first
        if self.langfuse_service and self.langfuse_service.is_available():
            logger.debug("Tentando buscar prompt do Langfuse")
            langfuse_prompt = self.langfuse_service.get_prompt(
                name="sql_generation_template",
                variables={"schema": self.schema_info, "question": user_question},
                label="production"
            )
            
            if langfuse_prompt:
                logger.info("Usando prompt do Langfuse")
                return langfuse_prompt
            else:
                logger.warning("Falha ao buscar prompt do Langfuse, usando template local")
        
        # Fallback to local prompt template
        logger.info("Usando template de prompt local")
        return get_fallback_prompt(
            "sql_generation_template",
            variables={"schema": self.schema_info, "question": user_question}
        )
    
    def convert_to_sql(self, user_question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Convert natural language question to SQL query"""
        logger.info(f"Convertendo pergunta para SQL: {user_question[:50]}...")
        try:
            prompt = self._create_sql_prompt(user_question)
            
            # Get system message from Langfuse or fallback
            system_content = None
            if self.langfuse_service and self.langfuse_service.is_available():
                system_content = self.langfuse_service.get_prompt(
                    name="sql_system_message",
                    label="production"
                )
                
            if not system_content:
                system_content = get_fallback_prompt("sql_system_message")
            
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=prompt)
            ]
            
            logger.info("Enviando prompt para LLM")
            response = self.llm.invoke(messages)
            sql_query = response.content.strip()
            logger.info(f"Query SQL gerada: {sql_query[:100]}...")
            
            # Extract token usage from response
            token_usage = self._extract_token_usage(response)
            estimated_cost = self._calculate_cost(token_usage) if token_usage else None
            
            # Remove markdown code blocks if present
            sql_query = re.sub(r'```sql\n?', '', sql_query)
            sql_query = re.sub(r'```\n?', '', sql_query)
            sql_query = sql_query.strip()
            
            # Extract SQL from response that might contain extra text
            # Look for SELECT statement in the response
            sql_lines = sql_query.split('\n')
            sql_parts = []
            found_select = False
            
            for line in sql_lines:
                line = line.strip()
                if not found_select:
                    # Look for the start of SELECT statement
                    if line.upper().startswith('SELECT'):
                        found_select = True
                        sql_parts.append(line)
                    elif 'SELECT' in line.upper():
                        # Extract from SELECT onwards
                        select_pos = line.upper().find('SELECT')
                        sql_parts.append(line[select_pos:])
                        found_select = True
                else:
                    # Continue collecting SQL lines
                    if line and not line.startswith('Question:') and not line.startswith('SQL Query:'):
                        sql_parts.append(line)
            
            if sql_parts:
                sql_query = ' '.join(sql_parts).strip()
            
            # Clean up any remaining prefixes
            sql_query = re.sub(r'^.*?SELECT', 'SELECT', sql_query, flags=re.IGNORECASE)
            sql_query = sql_query.strip()
            
            # Fix duplicate column patterns like "SELECT column, * FROM table"
            sql_query = self._fix_duplicate_columns(sql_query)
            
            # Validate query is SELECT only
            if not self._validate_select_only(sql_query):
                logger.error(f"Query rejeitada por conter comandos não-SELECT: {sql_query}")
                return {
                    "success": False,
                    "error": "Generated query contains non-SELECT statements",
                    "sql_query": None,
                    "result": None
                }
            
            logger.info("Query SQL validada com sucesso")
            return {
                "success": True,
                "error": None,
                "sql_query": sql_query,
                "result": None,
                "token_usage": token_usage,
                "estimated_cost": estimated_cost
            }
            
        except Exception as e:
            logger.error(f"Erro ao converter pergunta para SQL: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "sql_query": None,
                "result": None
            }
    
    def execute_query(self, sql_query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute the SQL query and return results"""
        logger.info(f"Executando query SQL: {sql_query[:100]}...")
        try:
            # Double-check query is safe
            if not self._validate_select_only(sql_query):
                logger.error(f"Query rejeitada na execução por conter comandos não-SELECT: {sql_query}")
                return {
                    "success": False,
                    "error": "Query contains non-SELECT statements",
                    "result": None
                }
            
            # Execute query
            logger.info("Conectando ao banco de dados")
            with self.engine.connect() as connection:
                result = connection.execute(text(sql_query))
                columns = list(result.keys())
                rows = result.fetchall()
                logger.info(f"Query executada com sucesso. {len(rows)} registros retornados")
                
                # Convert to pandas DataFrame for better display
                df = pd.DataFrame(rows, columns=columns)
                
                logger.info(f"DataFrame criado com {len(df)} linhas e {len(df.columns)} colunas")
                return {
                    "success": True,
                    "error": None,
                    "result": df,
                    "row_count": len(df)
                }
                
        except Exception as e:
            logger.error(f"Erro ao executar query SQL: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    def process_question(self, user_question: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Complete pipeline: convert question to SQL and execute with backward compatibility"""
        logger.info(f"Iniciando processamento completo da pergunta: {user_question[:50]}...")
        
        # Use session tracing if Langfuse is available
        if hasattr(self, 'langfuse_service') and self.langfuse_service and self.langfuse_service.is_available():
            try:
                # Try to use the new tracing system
                from core.langfuse_tracing import LangfuseTracing, TracingMetrics
                
                if not hasattr(self, 'langfuse_tracing'):
                    # Initialize tracing if not already done
                    try:
                        settings = get_dev_settings()
                        self.langfuse_tracing = LangfuseTracing(settings)
                    except Exception:
                        self.langfuse_tracing = None
                
                if hasattr(self, 'langfuse_tracing') and self.langfuse_tracing and self.langfuse_tracing.is_enabled():
                    with self.langfuse_tracing.trace_session(
                        session_name="text_to_sql_query",
                        user_id=user_id,
                        metadata={"question": user_question}
                    ) as session:
                        session_id = session.id if session else None
                        return self._process_with_legacy_compatibility(user_question, session_id)
                        
            except ImportError:
                pass  # Fall back to basic processing
        
        # Fallback to basic processing
        return self._process_with_legacy_compatibility(user_question, None)
    
    def _process_with_legacy_compatibility(self, user_question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process question with legacy compatibility and optional tracing"""
        import time
        start_time = time.time()
        
        # Convert to SQL
        sql_result = self.convert_to_sql(user_question, session_id)
        
        # Track SQL generation in Langfuse if available
        if hasattr(self, 'langfuse_tracing') and self.langfuse_tracing and self.langfuse_tracing.is_enabled():
            self.langfuse_tracing.track_sql_generation(
                user_question=user_question,
                generated_sql=sql_result.get("sql_query", ""),
                success=sql_result["success"],
                error_message=sql_result.get("error"),
                token_usage=sql_result.get("token_usage"),
                session_id=session_id
            )
            # Flush to ensure data is sent to dashboard
            self.langfuse_tracing.flush()
        
        if not sql_result["success"]:
            logger.error("Falha na conversão para SQL")
            return sql_result
        
        # Execute the query
        logger.info("Executando query gerada")
        execution_result = self.execute_query(sql_result["sql_query"], session_id)
        
        total_time = time.time() - start_time
        
        # Create enhanced result with tracing info if available
        final_result = {
            "success": execution_result["success"],
            "error": execution_result["error"],
            "sql_query": sql_result["sql_query"],
            "result": execution_result["result"],
            "total_time": total_time,
            "session_id": session_id
        }
        
        # Add token usage and cost estimation if available
        if sql_result.get("token_usage"):
            final_result["token_usage"] = sql_result["token_usage"]
            
            # Calculate estimated cost
            try:
                from core.langfuse_tracing import TracingMetrics
                estimated_cost = TracingMetrics.calculate_estimated_cost(
                    sql_result["token_usage"], 
                    getattr(self.settings if hasattr(self, 'settings') else get_dev_settings(), 'openai_model', 'gpt-3.5-turbo')
                )
                if estimated_cost:
                    final_result["estimated_cost"] = estimated_cost
            except ImportError:
                pass
        
        # Add other timing info if available
        if sql_result.get("execution_time"):
            final_result["sql_generation_time"] = sql_result["execution_time"]
        if execution_result.get("execution_time"):
            final_result["db_execution_time"] = execution_result["execution_time"]
        if execution_result.get("row_count"):
            final_result["row_count"] = execution_result["row_count"]
            
        # Add trace IDs if available
        if sql_result.get("trace_id"):
            final_result["sql_trace_id"] = sql_result["trace_id"]
        if execution_result.get("trace_id"):
            final_result["db_trace_id"] = execution_result["trace_id"]
        
        if final_result["success"]:
            logger.info("Processamento da pergunta concluído com sucesso")
        else:
            logger.error(f"Processamento da pergunta falhou: {final_result['error']}")
            
        return final_result