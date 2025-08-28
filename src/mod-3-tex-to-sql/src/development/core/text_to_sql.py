"""Text-to-SQL converter with comprehensive error handling and monitoring."""

import re
import time
from typing import Optional, Dict, Any

import pandas as pd
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from sqlalchemy import create_engine, inspect, text

from config.settings import DevSettings
from core.langfuse_service import LangfuseService, get_fallback_prompt
from core.langfuse_tracing import LangfuseTracing, TracingMetrics
from utils.logging_utils import get_logger

logger = get_logger(__name__)


class TextToSQLConverter:
    """Text-to-SQL converter with AI integration and comprehensive monitoring.
    
    Features:
        - Natural language to SQL query conversion using OpenAI
        - Database schema introspection and validation
        - Langfuse integration for prompt management and tracing
        - Security validation to prevent malicious queries
        - Comprehensive error handling and logging
    """
    
    def __init__(self, settings: DevSettings, openai_api_key: Optional[str] = None):
        """Initialize the converter with database connection and AI services.
        
        Args:
            settings: Development environment configuration
            openai_api_key: Optional OpenAI API key override
            
        Raises:
            ValueError: If OpenAI API key is not provided
            ConnectionError: If database connection fails
        """
        logger.info("Initializing TextToSQLConverter")
        
        self.settings = settings
        self.database_url = settings.database_url
        self.openai_api_key = openai_api_key or settings.openai_api_key
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required - set OPENAI_API_KEY environment variable")
            
        if not self.database_url:
            raise ValueError("Database URL is required - set DATABASE_URL environment variable")
        
        self._initialize_database_connection()
        self._initialize_ai_services()
        self._load_database_schema()
        
        logger.info("TextToSQLConverter initialized successfully")
    
    def _initialize_database_connection(self) -> None:
        """Initialize database connection with error handling."""
        try:
            self.engine = create_engine(self.database_url)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise ConnectionError(f"Failed to connect to database: {e}")
    
    def _initialize_ai_services(self) -> None:
        """Initialize AI services and integrations."""
        self.llm = ChatOpenAI(
            openai_api_key=self.openai_api_key,
            model=self.settings.openai_model,
            temperature=self.settings.temperature
        )
        
        self.langfuse_service = LangfuseService(self.settings)
        self.langfuse_tracing = LangfuseTracing(self.settings)
        
        logger.info("AI services initialized")
    
    def _load_database_schema(self) -> None:
        """Load and cache database schema information."""
        self.schema_info = self._get_database_schema()
        table_count = len(self.schema_info.split('Table:')) - 1
        logger.info(f"Schema loaded with {table_count} tables")
    
    def _get_database_schema(self) -> str:
        """Extract comprehensive database schema information.
        
        Returns:
            Formatted string containing table and column information
            
        Raises:
            DatabaseError: If schema extraction fails
        """
        try:
            inspector = inspect(self.engine)
            table_names = inspector.get_table_names()
            
            if not table_names:
                logger.warning("No tables found in database")
                return "No tables available"
            
            schema_parts = []
            
            for table_name in table_names:
                schema_parts.append(f"\nTable: {table_name}")
                columns = inspector.get_columns(table_name)
                
                for column in columns:
                    nullable_info = "NULL" if column['nullable'] else "NOT NULL"
                    schema_parts.append(
                        f"  - {column['name']}: {column['type']} {nullable_info}"
                    )
            
            logger.info(f"Schema extracted for {len(table_names)} tables")
            return "\n".join(schema_parts)
            
        except Exception as e:
            logger.error(f"Schema extraction failed: {e}")
            raise
    
    def _validate_select_only(self, sql_query: str) -> bool:
        """Validate SQL query contains only safe SELECT statements.
        
        Args:
            sql_query: SQL query to validate
            
        Returns:
            True if query is safe, False otherwise
        """
        if not sql_query or not sql_query.strip():
            return False
        
        normalized_query = re.sub(r'\s+', ' ', sql_query.strip().upper())
        
        # Remove SQL comments
        normalized_query = re.sub(r'--.*$', '', normalized_query, flags=re.MULTILINE)
        normalized_query = re.sub(r'/\*.*?\*/', '', normalized_query, flags=re.DOTALL)
        
        # Define dangerous SQL keywords
        dangerous_keywords = {
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE', 'EXECUTE'
        }
        
        # Check for dangerous keywords with word boundaries
        for keyword in dangerous_keywords:
            if re.search(rf'\b{keyword}\b', normalized_query):
                logger.warning(f"Blocked dangerous keyword: {keyword}")
                return False
        
        # Verify query starts with SELECT
        if not normalized_query.strip().startswith('SELECT'):
            logger.warning("Query must start with SELECT")
            return False
        
        return True
    
    def _create_sql_prompt(self, user_question: str) -> str:
        """Create optimized prompt for SQL generation with fallback strategy.
        
        Args:
            user_question: Natural language question from user
            
        Returns:
            Formatted prompt string for LLM
        """
        prompt_variables = {
            "schema": self.schema_info,
            "question": user_question
        }
        
        if self.langfuse_service.is_available():
            langfuse_prompt = self.langfuse_service.get_prompt(
                name="sql_generation_template",
                variables=prompt_variables,
                label="production"
            )
            
            if langfuse_prompt:
                logger.debug("Using Langfuse prompt template")
                return langfuse_prompt
        
        logger.debug("Using fallback prompt template")
        return get_fallback_prompt(
            "sql_generation_template",
            variables=prompt_variables
        )
    
    def convert_to_sql(self, user_question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Convert natural language question to SQL query with comprehensive tracking.
        
        Args:
            user_question: Natural language question to convert
            session_id: Optional session identifier for tracking
            
        Returns:
            Dictionary containing success status, SQL query, error info, and metrics
        """
        if not user_question or not user_question.strip():
            return self._create_error_response("Empty or invalid question provided")
        
        logger.info(f"Converting to SQL: {user_question[:50]}...")
        start_time = time.time()
        token_usage = None
        generation_id = None
        
        try:
            system_content = self._get_system_message()
            prompt = self._create_sql_prompt(user_question)
            
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=prompt)
            ]
            
            callbacks = self._get_tracing_callbacks()
            
            response = self.llm.invoke(
                messages, 
                config={"callbacks": callbacks} if callbacks else {}
            )
            
            sql_query = self._extract_sql_from_response(response.content)
            token_usage = TracingMetrics.extract_token_usage(response)
            
            if not self._validate_select_only(sql_query):
                return self._create_error_response(
                    "Generated query contains unsafe operations",
                    sql_query=sql_query,
                    execution_time=time.time() - start_time,
                    token_usage=token_usage,
                    session_id=session_id,
                    user_question=user_question
                )
            
            execution_time = time.time() - start_time
            generation_id = self._track_sql_generation(
                user_question, sql_query, True, None, execution_time, token_usage, session_id
            )
            
            return {
                "success": True,
                "error": None,
                "sql_query": sql_query,
                "result": None,
                "token_usage": token_usage,
                "execution_time": execution_time,
                "trace_id": generation_id
            }
            
        except Exception as e:
            logger.error(f"SQL conversion failed: {e}")
            return self._create_error_response(
                f"SQL generation failed: {e}",
                execution_time=time.time() - start_time,
                token_usage=token_usage,
                session_id=session_id,
                user_question=user_question
            )
    
    def execute_query(self, sql_query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute SQL query safely and return results with comprehensive tracking.
        
        Args:
            sql_query: SQL query to execute
            session_id: Optional session identifier for tracking
            
        Returns:
            Dictionary with execution results, metrics, and status
        """
        if not sql_query or not sql_query.strip():
            return {"success": False, "error": "Empty SQL query", "result": None}
        
        logger.info(f"Executing query: {sql_query[:100]}...")
        start_time = time.time()
        
        if not self._validate_select_only(sql_query):
            return self._create_query_error_response(
                "Query contains unsafe operations",
                sql_query, time.time() - start_time, session_id
            )
        
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql_query))
                columns = list(result.keys())
                rows = result.fetchall()
                
                df = pd.DataFrame(rows, columns=columns)
                execution_time = time.time() - start_time
                
                query_id = self._track_database_query(
                    sql_query, True, len(rows), None, execution_time, session_id
                )
                
                logger.info(f"Query executed successfully: {len(rows)} rows")
                
                return {
                    "success": True,
                    "error": None,
                    "result": df,
                    "row_count": len(rows),
                    "execution_time": execution_time,
                    "trace_id": query_id
                }
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Query execution failed: {e}")
            
            query_id = self._track_database_query(
                sql_query, False, 0, str(e), execution_time, session_id
            )
            
            return {
                "success": False,
                "error": str(e),
                "result": None,
                "execution_time": execution_time,
                "trace_id": query_id
            }
    
    def _get_system_message(self) -> str:
        """Get system message from Langfuse or fallback."""
        if self.langfuse_service.is_available():
            system_content = self.langfuse_service.get_prompt(
                name="sql_system_message",
                label="production"
            )
            if system_content:
                return system_content
        
        return get_fallback_prompt("sql_system_message")
    
    def _get_tracing_callbacks(self) -> list:
        """Get tracing callbacks if available."""
        callbacks = []
        if self.langfuse_tracing.is_enabled():
            callback_handler = self.langfuse_tracing.get_callback_handler()
            if callback_handler:
                callbacks.append(callback_handler)
        return callbacks
    
    def _extract_sql_from_response(self, response_content: str) -> str:
        """Extract clean SQL from LLM response."""
        if not response_content:
            return ""
        
        sql_query = response_content.strip()
        
        # Remove markdown code blocks
        sql_query = re.sub(r'```sql\n?', '', sql_query)
        sql_query = re.sub(r'```\n?', '', sql_query)
        
        # Extract SELECT statement from mixed content
        lines = sql_query.split('\n')
        sql_parts = []
        found_select = False
        
        for line in lines:
            line = line.strip()
            if not found_select and 'SELECT' in line.upper():
                if line.upper().startswith('SELECT'):
                    sql_parts.append(line)
                    found_select = True
                else:
                    # Extract from SELECT onwards
                    select_pos = line.upper().find('SELECT')
                    sql_parts.append(line[select_pos:])
                    found_select = True
            elif found_select and line and not any(
                line.startswith(prefix) for prefix in ['Question:', 'SQL Query:', 'Answer:']
            ):
                sql_parts.append(line)
        
        if sql_parts:
            sql_query = ' '.join(sql_parts).strip()
        
        # Final cleanup
        sql_query = re.sub(r'^.*?SELECT', 'SELECT', sql_query, flags=re.IGNORECASE)
        return sql_query.strip()
    
    def _create_error_response(
        self, 
        error_message: str, 
        sql_query: Optional[str] = None,
        execution_time: Optional[float] = None,
        token_usage: Optional[Dict] = None,
        session_id: Optional[str] = None,
        user_question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create standardized error response."""
        trace_id = None
        
        if user_question and self.langfuse_tracing.is_enabled():
            trace_id = self._track_sql_generation(
                user_question, sql_query or "", False, error_message,
                execution_time or 0.0, token_usage, session_id
            )
        
        return {
            "success": False,
            "error": error_message,
            "sql_query": sql_query,
            "result": None,
            "token_usage": token_usage,
            "execution_time": execution_time or 0.0,
            "trace_id": trace_id
        }
    
    def _create_query_error_response(
        self, error_message: str, sql_query: str, 
        execution_time: float, session_id: Optional[str]
    ) -> Dict[str, Any]:
        """Create error response for query execution failures."""
        query_id = self._track_database_query(
            sql_query, False, 0, error_message, execution_time, session_id
        )
        
        return {
            "success": False,
            "error": error_message,
            "result": None,
            "execution_time": execution_time,
            "trace_id": query_id
        }
    
    def _track_sql_generation(
        self, user_question: str, sql_query: str, success: bool,
        error_message: Optional[str], execution_time: float,
        token_usage: Optional[Dict], session_id: Optional[str]
    ) -> Optional[str]:
        """Track SQL generation with Langfuse if available."""
        if not self.langfuse_tracing.is_enabled():
            return None
        
        return self.langfuse_tracing.track_sql_generation(
            user_question=user_question,
            generated_sql=sql_query,
            success=success,
            error_message=error_message,
            execution_time=execution_time,
            token_usage=token_usage,
            session_id=session_id
        )
    
    def _track_database_query(
        self, sql_query: str, success: bool, row_count: int,
        error_message: Optional[str], execution_time: float,
        session_id: Optional[str]
    ) -> Optional[str]:
        """Track database query execution with Langfuse if available."""
        if not self.langfuse_tracing.is_enabled():
            return None
        
        return self.langfuse_tracing.track_database_query(
            sql_query=sql_query,
            success=success,
            row_count=row_count,
            error_message=error_message,
            execution_time=execution_time,
            session_id=session_id
        )
    
    def process_question(self, user_question: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Complete text-to-SQL pipeline with comprehensive tracking.
        
        Args:
            user_question: Natural language question to process
            user_id: Optional user identifier for tracking
            
        Returns:
            Complete processing results with SQL, data, and metrics
        """
        if not user_question or not user_question.strip():
            return {"success": False, "error": "Empty question provided"}
        
        logger.info(f"Processing question: {user_question[:50]}...")
        
        if self.langfuse_tracing.is_enabled():
            with self.langfuse_tracing.trace_session(
                session_name="text_to_sql_query",
                user_id=user_id,
                metadata={"question": user_question}
            ) as session:
                session_id = session.id if session else None
                return self._process_with_session(user_question, session_id)
        
        return self._process_with_session(user_question, None)
    
    def _process_with_session(self, user_question: str, session_id: Optional[str]) -> Dict[str, Any]:
        """Process question with optional session tracking.
        
        Args:
            user_question: Question to process
            session_id: Optional session identifier
            
        Returns:
            Complete processing results with timing and cost information
        """
        start_time = time.time()
        
        sql_result = self.convert_to_sql(user_question, session_id)
        
        if not sql_result["success"]:
            return sql_result
        
        execution_result = self.execute_query(sql_result["sql_query"], session_id)
        total_time = time.time() - start_time
        
        estimated_cost = None
        if sql_result.get("token_usage"):
            estimated_cost = TracingMetrics.calculate_estimated_cost(
                sql_result["token_usage"], self.settings.openai_model
            )
        
        result = {
            "success": execution_result["success"],
            "error": execution_result["error"],
            "sql_query": sql_result["sql_query"],
            "result": execution_result["result"],
            "row_count": execution_result.get("row_count"),
            "token_usage": sql_result.get("token_usage"),
            "estimated_cost": estimated_cost,
            "sql_generation_time": sql_result.get("execution_time"),
            "db_execution_time": execution_result.get("execution_time"),
            "total_time": total_time,
            "session_id": session_id,
            "sql_trace_id": sql_result.get("trace_id"),
            "db_trace_id": execution_result.get("trace_id")
        }
        
        if result["success"]:
            logger.info("Question processed successfully")
            if estimated_cost:
                logger.info(f"Estimated cost: ${estimated_cost:.6f}")
        else:
            logger.error(f"Processing failed: {result['error']}")
        
        if self.langfuse_tracing.is_enabled():
            self.langfuse_tracing.flush()
        
        return result