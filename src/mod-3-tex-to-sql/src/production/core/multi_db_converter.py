import re
import logging
import os
import uuid
from typing import Optional, Dict, Any, List, Union
from sqlalchemy import create_engine, inspect, text
import pandas as pd
from dotenv import load_dotenv
from dataclasses import dataclass
from enum import Enum

# Disable telemetry to reduce errors and improve performance
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['POSTHOG_DISABLE'] = 'true'
os.environ['CHROMA_TELEMETRY'] = 'False'

# Vanna.ai imports
from vanna.qdrant.qdrant_vector import Qdrant_VectorStore
from vanna.openai.openai_chat import OpenAI_Chat
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

# Configuration imports
from config.settings import get_settings

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    POSTGRESQL = "postgresql"
    QDRANT = "qdrant"


@dataclass
class DatabaseConfig:
    db_type: DatabaseType
    connection_string: str
    api_key: Optional[str] = None
    collection_name: Optional[str] = None


@dataclass
class QueryResult:
    success: bool
    data: Optional[Union[pd.DataFrame, List[Dict]]]
    error: Optional[str] = None
    query: Optional[str] = None
    database_type: Optional[DatabaseType] = None


class VannaQdrant(Qdrant_VectorStore, OpenAI_Chat):
    """Custom Vanna class combining Qdrant vector store with OpenAI chat"""
    def __init__(self, config=None):
        Qdrant_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)


class MultiDatabaseVannaConverter:
    """Enhanced Vanna Text-to-SQL converter supporting both PostgreSQL and Qdrant"""
    
    def __init__(self, 
                 postgres_url: Optional[str] = None, 
                 qdrant_url: Optional[str] = None,
                 qdrant_api_key: Optional[str] = None,
                 openai_api_key: Optional[str] = None):
        logger.info("Inicializando MultiDatabaseVannaConverter")
        
        # Get settings with fallback to parameters for backward compatibility
        settings = get_settings()
        
        postgres_url = postgres_url or settings.database_url
        qdrant_url = qdrant_url or settings.qdrant_url
        qdrant_api_key = qdrant_api_key or settings.qdrant_api_key
        self.openai_api_key = openai_api_key or settings.openai_api_key
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")
        
        # Setup database configurations
        self.databases = {
            DatabaseType.POSTGRESQL: DatabaseConfig(
                db_type=DatabaseType.POSTGRESQL,
                connection_string=postgres_url
            ),
            DatabaseType.QDRANT: DatabaseConfig(
                db_type=DatabaseType.QDRANT,
                connection_string=qdrant_url,
                api_key=qdrant_api_key,
                collection_name=settings.qdrant_collection_ubereats
            )
        }
        
        # Initialize connections
        self._setup_postgresql_connection()
        self._setup_qdrant_connection()
        self._setup_vanna_ai()
        
        logger.info("MultiDatabaseVannaConverter inicializado com sucesso")
    
    def _setup_postgresql_connection(self):
        """Setup PostgreSQL connection"""
        try:
            self.postgres_engine = create_engine(self.databases[DatabaseType.POSTGRESQL].connection_string)
            # Test connection
            with self.postgres_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Conexão PostgreSQL estabelecida com sucesso")
        except Exception as e:
            logger.error(f"Erro ao conectar ao PostgreSQL: {e}")
            raise
    
    def _setup_qdrant_connection(self):
        """Setup Qdrant connection"""
        try:
            qdrant_config = self.databases[DatabaseType.QDRANT]
            self.qdrant_client = QdrantClient(
                url=qdrant_config.connection_string,
                api_key=qdrant_config.api_key
            )
            
            # Test connection
            collections = self.qdrant_client.get_collections()
            logger.info(f"Conexão Qdrant estabelecida. Collections disponíveis: {len(collections.collections)}")
            
            # Ensure our collection exists
            self._ensure_qdrant_collection()
            
        except Exception as e:
            logger.error(f"Erro ao conectar ao Qdrant: {e}")
            raise
    
    def _ensure_qdrant_collection(self):
        """Ensure Qdrant collection exists"""
        try:
            collection_name = self.databases[DatabaseType.QDRANT].collection_name
            collections = self.qdrant_client.get_collections()
            
            if collection_name not in [col.name for col in collections.collections]:
                # Create collection if it doesn't exist
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # OpenAI embedding size
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection '{collection_name}' criada no Qdrant")
            else:
                logger.info(f"Collection '{collection_name}' já existe no Qdrant")
                
        except Exception as e:
            logger.warning(f"Erro ao verificar/criar collection Qdrant: {e}")
    
    def _setup_vanna_ai(self):
        """Setup Vanna.ai with Qdrant vector store"""
        try:
            # Create unique collection name for Vanna
            vanna_collection_name = f"vanna_ubereats_{str(uuid.uuid4())[:8]}"
            
            # Initialize Vanna with Qdrant using settings
            settings = get_settings()
            self.vn = VannaQdrant(config={
                'client': self.qdrant_client,
                'collection_name': vanna_collection_name,
                'api_key': self.openai_api_key,
                'model': settings.openai_model
            })
            
            logger.info("Vanna.ai configurado com Qdrant vector store")
            
            # Setup database connection for Vanna
            self._connect_vanna_to_postgres()
            
            # Train initial schema
            self._train_initial_schema()
            
        except Exception as e:
            logger.error(f"Erro ao configurar Vanna.ai: {e}")
            raise
    
    def _connect_vanna_to_postgres(self):
        """Connect Vanna to PostgreSQL"""
        try:
            postgres_config = self.databases[DatabaseType.POSTGRESQL]
            import urllib.parse
            parsed = urllib.parse.urlparse(postgres_config.connection_string)
            
            self.vn.connect_to_postgres(
                host=parsed.hostname,
                dbname=parsed.path.lstrip('/'),
                user=parsed.username,
                password=parsed.password,
                port=parsed.port or 5432
            )
            logger.info("Vanna.ai conectado ao PostgreSQL")
            
        except Exception as e:
            logger.warning(f"Erro ao conectar Vanna ao PostgreSQL: {e}")
    
    def _train_initial_schema(self):
        """Train Vanna with PostgreSQL schema information"""
        logger.info("Treinando Vanna.ai com schema PostgreSQL")
        try:
            inspector = inspect(self.postgres_engine)
            table_names = inspector.get_table_names()
            
            # Train with DDL information
            for table_name in table_names:
                columns = inspector.get_columns(table_name)
                
                ddl_info = f"Table: {table_name}\n"
                for column in columns:
                    col_type = str(column['type'])
                    nullable = "NULL" if column['nullable'] else "NOT NULL"
                    ddl_info += f"  - {column['name']}: {col_type} {nullable}\n"
                
                try:
                    self.vn.train(ddl=ddl_info)
                    logger.debug(f"Schema da tabela {table_name} treinado")
                except Exception as train_error:
                    logger.warning(f"Erro ao treinar tabela {table_name}: {train_error}")
            
            # Add multi-database context
            domain_context = """
            Context: Multi-database system for UberEats Brasil
            - PostgreSQL contains structured relational data (invoices, restaurants, transactions)
            - Qdrant contains vector embeddings and unstructured data
            - Use PostgreSQL for traditional SQL queries on structured data
            - Use Qdrant for similarity search and vector operations
            - Common PostgreSQL tables: extracted_invoices, vendors, customers
            - Support both Portuguese and English queries
            """
            self.vn.train(documentation=domain_context)
            logger.info("Contexto multi-database treinado")
            
        except Exception as e:
            logger.error(f"Erro ao treinar schema inicial: {e}")
    
    def _detect_query_type(self, user_question: str) -> DatabaseType:
        """Detect which database should handle the query based on question content"""
        question_lower = user_question.lower()
        
        # Vector/similarity search keywords indicate Qdrant
        vector_keywords = [
            'similar', 'parecido', 'semelhante', 'embedding', 'vector', 'vetor',
            'search', 'busca', 'find', 'encontrar', 'matching', 'correspondente',
            'closest', 'nearest', 'mais próximo', 'recommendation', 'recomendação'
        ]
        
        # SQL/structured data keywords indicate PostgreSQL
        sql_keywords = [
            'count', 'sum', 'avg', 'max', 'min', 'group by', 'order by',
            'join', 'where', 'total', 'soma', 'média', 'máximo', 'mínimo',
            'invoice', 'nota fiscal', 'restaurant', 'restaurante', 'vendor',
            'fornecedor', 'amount', 'valor', 'date', 'data'
        ]
        
        # Check for vector search indicators
        if any(keyword in question_lower for keyword in vector_keywords):
            return DatabaseType.QDRANT
        
        # Check for SQL indicators
        if any(keyword in question_lower for keyword in sql_keywords):
            return DatabaseType.POSTGRESQL
        
        # Default to PostgreSQL for traditional queries
        return DatabaseType.POSTGRESQL
    
    def _validate_select_only(self, sql_query: str) -> bool:
        """Validate that the query contains only SELECT statements"""
        sql_normalized = re.sub(r'\s+', ' ', sql_query.strip().upper())
        
        # Remove comments
        sql_normalized = re.sub(r'--.*$', '', sql_normalized, flags=re.MULTILINE)
        sql_normalized = re.sub(r'/\*.*?\*/', '', sql_normalized, flags=re.DOTALL)
        
        # Check for dangerous keywords
        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
            'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in sql_normalized:
                return False
        
        return sql_normalized.strip().startswith('SELECT')
    
    def query_postgresql(self, user_question: str) -> QueryResult:
        """Query PostgreSQL using Vanna.ai for SQL generation"""
        logger.info(f"Consultando PostgreSQL: {user_question[:50]}...")
        
        try:
            # Generate SQL using Vanna
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                sql_query = self.vn.generate_sql(user_question)
            
            if not sql_query or sql_query.strip() == '':
                return QueryResult(
                    success=False,
                    data=None,
                    error="Não foi possível gerar query SQL",
                    database_type=DatabaseType.POSTGRESQL
                )
            
            # Validate query safety
            if not self._validate_select_only(sql_query):
                return QueryResult(
                    success=False,
                    data=None,
                    error="Query contém comandos não permitidos (apenas SELECT é permitido)",
                    query=sql_query,
                    database_type=DatabaseType.POSTGRESQL
                )
            
            # Execute query
            with self.postgres_engine.connect() as connection:
                result = connection.execute(text(sql_query))
                columns = list(result.keys())
                rows = result.fetchall()
                
                df = pd.DataFrame(rows, columns=columns)
                
                return QueryResult(
                    success=True,
                    data=df,
                    query=sql_query,
                    database_type=DatabaseType.POSTGRESQL
                )
                
        except Exception as e:
            logger.error(f"Erro ao consultar PostgreSQL: {e}")
            return QueryResult(
                success=False,
                data=None,
                error=str(e),
                database_type=DatabaseType.POSTGRESQL
            )
    
    def query_qdrant(self, user_question: str, limit: int = 10) -> QueryResult:
        """Query Qdrant for vector similarity search"""
        logger.info(f"Consultando Qdrant: {user_question[:50]}...")
        
        try:
            collection_name = self.databases[DatabaseType.QDRANT].collection_name
            
            # Generate embedding for the question using OpenAI
            from openai import OpenAI
            openai_client = OpenAI(api_key=self.openai_api_key)
            
            response = openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=user_question
            )
            query_vector = response.data[0].embedding
            
            # Search in Qdrant
            search_result = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # Convert results to DataFrame-like structure
            results_data = []
            for point in search_result:
                result_item = {
                    'id': point.id,
                    'score': point.score,
                    **point.payload
                }
                results_data.append(result_item)
            
            df = pd.DataFrame(results_data)
            
            return QueryResult(
                success=True,
                data=df,
                query=f"Vector similarity search for: {user_question}",
                database_type=DatabaseType.QDRANT
            )
            
        except Exception as e:
            logger.error(f"Erro ao consultar Qdrant: {e}")
            return QueryResult(
                success=False,
                data=None,
                error=str(e),
                database_type=DatabaseType.QDRANT
            )
    
    def insert_to_qdrant(self, data: List[Dict[str, Any]], vectors: Optional[List[List[float]]] = None) -> bool:
        """Insert data into Qdrant collection"""
        try:
            collection_name = self.databases[DatabaseType.QDRANT].collection_name
            
            points = []
            for i, item in enumerate(data):
                point_id = item.get('id', str(uuid.uuid4()))
                vector = vectors[i] if vectors else self._generate_embedding(str(item))
                
                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=item
                ))
            
            self.qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            logger.info(f"Inseridos {len(points)} pontos no Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inserir dados no Qdrant: {e}")
            return False
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=self.openai_api_key)
            
            response = openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {e}")
            return [0.0] * 1536  # Return zero vector as fallback
    
    def process_question(self, user_question: str) -> QueryResult:
        """Process question and route to appropriate database"""
        logger.info(f"Processando pergunta: {user_question[:50]}...")
        
        # Detect which database to use
        db_type = self._detect_query_type(user_question)
        logger.info(f"Roteando para: {db_type.value}")
        
        if db_type == DatabaseType.POSTGRESQL:
            return self.query_postgresql(user_question)
        elif db_type == DatabaseType.QDRANT:
            return self.query_qdrant(user_question)
        else:
            return QueryResult(
                success=False,
                data=None,
                error="Tipo de consulta não reconhecido"
            )
    
    def train_model(self, question: str, sql: str) -> Dict[str, Any]:
        """Train Vanna model with question-SQL pairs for PostgreSQL queries"""
        logger.info(f"Treinando modelo: {question[:50]}...")
        try:
            if not self._validate_select_only(sql):
                return {
                    "success": False,
                    "error": "SQL de treinamento deve conter apenas comandos SELECT"
                }
            
            self.vn.train(question=question, sql=sql)
            logger.info("Modelo treinado com sucesso")
            
            return {"success": True, "error": None}
            
        except Exception as e:
            logger.error(f"Erro ao treinar modelo: {e}")
            return {"success": False, "error": str(e)}
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about connected databases"""
        info = {
            "databases": {
                "postgresql": {
                    "type": "Relational Database",
                    "status": "connected",
                    "tables": []
                },
                "qdrant": {
                    "type": "Vector Database", 
                    "status": "connected",
                    "collections": []
                }
            }
        }
        
        try:
            # Get PostgreSQL table info
            inspector = inspect(self.postgres_engine)
            info["databases"]["postgresql"]["tables"] = inspector.get_table_names()
        except Exception as e:
            info["databases"]["postgresql"]["status"] = f"error: {e}"
        
        try:
            # Get Qdrant collection info
            collections = self.qdrant_client.get_collections()
            info["databases"]["qdrant"]["collections"] = [col.name for col in collections.collections]
        except Exception as e:
            info["databases"]["qdrant"]["status"] = f"error: {e}"
        
        return info