import re
import logging
import os
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, text
import pandas as pd
from dotenv import load_dotenv
from dataclasses import dataclass
from enum import Enum

# Disable telemetry
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['POSTHOG_DISABLE'] = 'true'
os.environ['CHROMA_TELEMETRY'] = 'False'

# Import existing Vanna converter
from vanna_converter import VannaTextToSQLConverter
# Configuration imports
from config.settings import get_settings

# Qdrant imports
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class QueryType(Enum):
    POSTGRES_ONLY = "postgres_only"
    QDRANT_ONLY = "qdrant_only"
    CROSS_DATABASE = "cross_database"


@dataclass
class QueryIntent:
    query_type: QueryType
    menu_criteria: Optional[str] = None
    financial_question: Optional[str] = None
    qdrant_filters: Optional[Dict] = None


@dataclass
class CrossDatabaseResult:
    success: bool
    data: Optional[pd.DataFrame] = None
    error: Optional[str] = None
    query: Optional[str] = None
    qdrant_filter_used: Optional[str] = None
    restaurants_found: Optional[int] = None
    execution_plan: Optional[str] = None


class EnhancedVannaConverter:
    """
    Enhanced Vanna converter that can handle cross-database queries
    combining menu data from Qdrant with financial data from PostgreSQL
    """
    
    def __init__(self, 
                 postgres_url: Optional[str] = None,
                 qdrant_url: Optional[str] = None, 
                 qdrant_api_key: Optional[str] = None,
                 openai_api_key: Optional[str] = None):
        
        logger.info("Inicializando EnhancedVannaConverter")
        
        # Get settings with fallback to parameters for backward compatibility
        settings = get_settings()
        
        postgres_url = postgres_url or settings.database_url
        qdrant_url = qdrant_url or settings.qdrant_url
        qdrant_api_key = qdrant_api_key or settings.qdrant_api_key
        openai_api_key = openai_api_key or settings.openai_api_key
        
        # Initialize the original Vanna converter for PostgreSQL
        self.vanna_converter = VannaTextToSQLConverter(
            database_url=postgres_url,
            openai_api_key=openai_api_key
        )
        
        # Initialize Qdrant client for menu data queries
        self.qdrant_client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key
        )
        
        # Configuration from settings
        self.qdrant_collection = settings.qdrant_collection_menu
        self.openai_api_key = openai_api_key
        
        # Verify Qdrant connection
        try:
            collections = self.qdrant_client.get_collections()
            logger.info(f"Conectado ao Qdrant. Collections: {[c.name for c in collections.collections]}")
        except Exception as e:
            logger.warning(f"Qdrant connection issue: {e}")
        
        logger.info("EnhancedVannaConverter inicializado com sucesso")
    
    def _analyze_query_intent(self, question: str) -> QueryIntent:
        """Analyze user question to determine query intent and routing"""
        question_lower = question.lower()
        
        # Menu/cuisine related keywords
        menu_keywords = [
            'mexicanos', 'mexicana', 'mexican',
            'vegetarianos', 'vegetariana', 'vegetarian',
            'culinária', 'cuisine', 'tipo de comida',
            'cardápio', 'menu', 'pratos',
            'italiano', 'italiana', 'italian',
            'japonês', 'japonesa', 'japanese',
            'sem glúten', 'gluten free',
            'vegano', 'vegan',
            'aperitivos', 'entradas', 'sobremesas',
            'guacamole', 'chips', 'sushi', 'pizza', 'hambúrguer'
        ]
        
        # Financial/invoice related keywords  
        finance_keywords = [
            'faturamento', 'revenue', 'receita',
            'ticket médio', 'ticket medio', 'average ticket',
            'notas fiscais', 'invoices', 'faturas',
            'valores', 'amounts', 'valor total',
            'vendas', 'sales', 'pedidos',
            'performance', 'crescimento', 'growth'
        ]
        
        # Check for keywords
        has_menu = any(keyword in question_lower for keyword in menu_keywords)
        has_finance = any(keyword in question_lower for keyword in finance_keywords)
        
        logger.info(f"Query analysis - Menu: {has_menu}, Finance: {has_finance}")
        
        if has_menu and has_finance:
            # Cross-database query
            return QueryIntent(
                query_type=QueryType.CROSS_DATABASE,
                menu_criteria=self._extract_menu_criteria(question_lower),
                financial_question=self._extract_financial_question(question)
            )
        elif has_menu and not has_finance:
            # Qdrant only
            return QueryIntent(
                query_type=QueryType.QDRANT_ONLY,
                menu_criteria=question
            )
        else:
            # PostgreSQL only (default)
            return QueryIntent(
                query_type=QueryType.POSTGRES_ONLY,
                financial_question=question
            )
    
    def _extract_menu_criteria(self, question_lower: str) -> str:
        """Extract menu-related criteria from question"""
        # Hard-coded patterns for minimum implementation
        if 'mexicanos' in question_lower or 'mexicana' in question_lower:
            return 'Mexican'
        elif 'vegetarianos' in question_lower or 'vegetariana' in question_lower:
            return 'vegetarian'
        elif 'italiano' in question_lower or 'italiana' in question_lower:
            return 'Italian'
        elif 'japonês' in question_lower or 'japonesa' in question_lower:
            return 'Japanese'
        elif 'sem glúten' in question_lower:
            return 'gluten_free'
        elif 'vegano' in question_lower:
            return 'vegan'
        elif 'aperitivos' in question_lower or 'entradas' in question_lower:
            return 'appetizers'
        else:
            return question_lower  # Fallback to full question
    
    def _extract_financial_question(self, question: str) -> str:
        """Extract financial question part, removing menu criteria"""
        # Simple approach: replace menu terms with generic terms
        financial_question = question
        
        # Replace specific cuisine mentions with generic "restaurants"
        replacements = {
            'restaurantes mexicanos': 'restaurantes',
            'restaurantes vegetarianos': 'restaurantes',
            'restaurantes italianos': 'restaurantes',
            'restaurantes japoneses': 'restaurantes',
            'restaurantes com': 'restaurantes',
            'que servem.*?e': '',
            'que têm.*?no cardápio': ''
        }
        
        for pattern, replacement in replacements.items():
            financial_question = re.sub(pattern, replacement, financial_question, flags=re.IGNORECASE)
        
        return financial_question.strip()
    
    def _filter_restaurants_by_menu(self, criteria: str) -> List[str]:
        """Query Qdrant to filter restaurants based on menu criteria"""
        try:
            logger.info(f"Filtering restaurants by: {criteria}")
            
            # Create search based on criteria type
            if criteria == 'Mexican':
                # Use scroll to find Mexican restaurants by cuisine type
                all_results = self.qdrant_client.scroll(
                    collection_name=self.qdrant_collection,
                    limit=1000,
                    with_payload=True,
                    with_vectors=False
                )
                
                # Filter for Mexican cuisine
                filtered_results = []
                for point in all_results[0]:
                    if point.payload:
                        cuisine_type = point.payload.get('cuisine_type', '')
                        if cuisine_type == 'Mexican':
                            filtered_results.append(point)
                
                search_results = [filtered_results, None]
            elif criteria == 'vegetarian':
                # Use scroll with text search since vector search isn't working well
                # Get all points and filter by text content
                all_results = self.qdrant_client.scroll(
                    collection_name=self.qdrant_collection,
                    limit=1000,  # Get more points to search through
                    with_payload=True,
                    with_vectors=False
                )
                
                # Filter for vegetarian content
                filtered_results = []
                for point in all_results[0]:
                    if point.payload:
                        # Check if item contains vegetarian indicators
                        payload_text = str(point.payload).lower()
                        if any(veg_term in payload_text for veg_term in [
                            'vegetariano', 'vegetarian', 'vegetal',
                            'dietary_tags', 'is_vegetarian'
                        ]):
                            # Double-check it's actually vegetarian
                            dietary_tags = point.payload.get('dietary_tags', [])
                            is_vegetarian = point.payload.get('is_vegetarian', False)
                            
                            if (isinstance(dietary_tags, list) and 'Vegetariano' in dietary_tags) or \
                               is_vegetarian or \
                               'vegetariano' in payload_text:
                                filtered_results.append(point)
                
                search_results = [filtered_results, None]
            elif criteria == 'gluten_free':
                # Use scroll to find gluten-free restaurants (same pattern as Mexican/vegetarian)
                all_results = self.qdrant_client.scroll(
                    collection_name=self.qdrant_collection,
                    limit=1000,
                    with_payload=True,
                    with_vectors=False
                )
                
                # Filter for gluten-free content
                filtered_results = []
                for point in all_results[0]:
                    if point.payload:
                        # Check dietary_tags for gluten-free indicators
                        dietary_tags = point.payload.get('dietary_tags', [])
                        is_gluten_free = point.payload.get('is_gluten_free', False)
                        payload_text = str(point.payload).lower()
                        
                        # Check various gluten-free indicators
                        gluten_free_terms = ['sem glúten', 'gluten free', 'sem gluten', 'gluten-free']
                        if (isinstance(dietary_tags, list) and any(
                            'sem glúten' in str(tag).lower() or 'gluten free' in str(tag).lower() 
                            for tag in dietary_tags
                        )) or is_gluten_free or any(term in payload_text for term in gluten_free_terms):
                            filtered_results.append(point)
                
                search_results = [filtered_results, None]
            elif criteria == 'appetizers':
                # Use scroll to find restaurants with appetizers
                all_results = self.qdrant_client.scroll(
                    collection_name=self.qdrant_collection,
                    limit=1000,
                    with_payload=True,
                    with_vectors=False
                )
                
                # Filter for appetizers/entradas
                filtered_results = []
                for point in all_results[0]:
                    if point.payload:
                        # Check category and item names for appetizers
                        category = point.payload.get('category', '')
                        item_name = point.payload.get('item_name', '')
                        payload_text = str(point.payload).lower()
                        
                        # Check for appetizer indicators
                        appetizer_terms = ['entradas', 'appetizer', 'aperitivo', 'entrada']
                        if (category == 'Entradas' or 
                            any(term in payload_text for term in appetizer_terms) or
                            any(term in item_name.lower() for term in appetizer_terms)):
                            filtered_results.append(point)
                
                search_results = [filtered_results, None]
            else:
                # Fallback: check if the criteria contains vegetarian keywords
                criteria_lower = criteria.lower()
                if 'vegetarian' in criteria_lower or 'vegetariano' in criteria_lower:
                    # Use the same vegetarian logic
                    all_results = self.qdrant_client.scroll(
                        collection_name=self.qdrant_collection,
                        limit=1000,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    filtered_results = []
                    for point in all_results[0]:
                        if point.payload:
                            payload_text = str(point.payload).lower()
                            dietary_tags = point.payload.get('dietary_tags', [])
                            is_vegetarian = point.payload.get('is_vegetarian', False)
                            
                            if (isinstance(dietary_tags, list) and 'Vegetariano' in dietary_tags) or \
                               is_vegetarian or \
                               'vegetariano' in payload_text:
                                filtered_results.append(point)
                    
                    search_results = [filtered_results, None]
                else:
                    # Semantic search fallback
                    from openai import OpenAI
                    openai_client = OpenAI(api_key=self.openai_api_key)
                    
                    response = openai_client.embeddings.create(
                        model="text-embedding-ada-002",
                        input=criteria
                    )
                    query_vector = response.data[0].embedding
                    
                    search_results = self.qdrant_client.search(
                        collection_name=self.qdrant_collection,
                        query_vector=query_vector,
                        limit=50,
                        with_payload=True
                    )
                    
                    # Convert search results to scroll format
                    search_results = [search_results, None]
            
            # Extract unique restaurant names
            restaurant_names = set()
            
            # search_results is always [points_list, None] from above
            points = search_results[0]
            
            for point in points:
                if hasattr(point, 'payload') and point.payload:
                    restaurant_name = point.payload.get('restaurant_name')
                    if restaurant_name:
                        restaurant_names.add(restaurant_name)
            
            restaurant_list = list(restaurant_names)
            logger.info(f"Found {len(restaurant_list)} restaurants matching criteria: {restaurant_list[:5]}...")
            
            return restaurant_list
            
        except Exception as e:
            logger.error(f"Error filtering restaurants: {e}")
            return []
    
    def _generate_filtered_sql(self, financial_question: str, restaurant_names: List[str]) -> str:
        """Generate SQL with restaurant filter using Vanna"""
        try:
            # First, get base SQL from Vanna
            sql_result = self.vanna_converter.convert_to_sql(financial_question)
            
            if not sql_result["success"]:
                raise Exception(f"Vanna SQL generation failed: {sql_result['error']}")
            
            base_sql = sql_result["sql_query"].strip()
            
            # Remove trailing semicolon if present
            if base_sql.endswith(';'):
                base_sql = base_sql[:-1]
                
            # Normalize SQL by replacing newlines with spaces for easier parsing
            base_sql = ' '.join(base_sql.split())
            
            # Add restaurant filter to WHERE clause
            if restaurant_names:
                # Create restaurant name list for SQL IN clause
                quoted_names = [f"'{name.replace('\'', '\'\'')}'" for name in restaurant_names]
                restaurant_filter = f"vendor_name IN ({', '.join(quoted_names)})"
                
                # Add WHERE clause or extend existing one
                base_sql_upper = base_sql.upper()
                
                if ' WHERE ' in base_sql_upper:
                    # Find the WHERE clause and add the filter to it
                    where_pos = base_sql_upper.find(' WHERE ')
                    
                    # Find the end of the WHERE clause (before GROUP BY, ORDER BY, etc.)
                    where_end = len(base_sql)
                    for clause in [' GROUP BY', ' ORDER BY', ' HAVING', ' LIMIT']:
                        pos = base_sql_upper.find(clause, where_pos)
                        if pos != -1:
                            where_end = min(where_end, pos)
                    
                    # Insert the restaurant filter into the WHERE clause
                    filtered_sql = (base_sql[:where_end] + 
                                  f" AND {restaurant_filter}" + 
                                  base_sql[where_end:])
                else:
                    # Add new WHERE clause
                    # Find the position to insert WHERE (before ORDER BY, GROUP BY, etc.)
                    insert_position = len(base_sql)
                    for clause in [' ORDER BY', ' GROUP BY', ' HAVING', ' LIMIT']:
                        pos = base_sql_upper.find(clause)
                        if pos != -1:
                            insert_position = min(insert_position, pos)
                    
                    filtered_sql = (base_sql[:insert_position] + 
                                  f" WHERE {restaurant_filter}" + 
                                  base_sql[insert_position:])
            else:
                # No restaurants found, add impossible condition
                filtered_sql = base_sql + " WHERE 1=0"
            
            logger.info(f"Base SQL: {base_sql}")
            logger.info(f"Restaurant filter: {restaurant_filter}")
            logger.info(f"Generated filtered SQL: {filtered_sql}")
            return filtered_sql
            
        except Exception as e:
            logger.error(f"Error generating filtered SQL: {e}")
            raise
    
    def process_question(self, user_question: str) -> CrossDatabaseResult:
        """Main entry point - process question with cross-database capability"""
        logger.info(f"Processing question: {user_question[:100]}...")
        
        try:
            # Analyze query intent
            intent = self._analyze_query_intent(user_question)
            logger.info(f"Query intent: {intent.query_type}")
            
            if intent.query_type == QueryType.POSTGRES_ONLY:
                # Use original Vanna converter
                result = self.vanna_converter.process_question(user_question)
                return CrossDatabaseResult(
                    success=result["success"],
                    data=result["result"],
                    error=result["error"],
                    query=result["sql_query"],
                    execution_plan="PostgreSQL only"
                )
            
            elif intent.query_type == QueryType.QDRANT_ONLY:
                # Query Qdrant for menu data
                restaurant_names = self._filter_restaurants_by_menu(intent.menu_criteria)
                
                # Convert to DataFrame
                menu_data = []
                for name in restaurant_names:
                    menu_data.append({"restaurant_name": name})
                
                return CrossDatabaseResult(
                    success=True,
                    data=pd.DataFrame(menu_data),
                    query=f"Qdrant filter: {intent.menu_criteria}",
                    restaurants_found=len(restaurant_names),
                    execution_plan="Qdrant only"
                )
            
            elif intent.query_type == QueryType.CROSS_DATABASE:
                # Cross-database execution
                logger.info("Executing cross-database query")
                
                # Step 1: Filter restaurants from Qdrant
                restaurant_names = self._filter_restaurants_by_menu(intent.menu_criteria)
                
                if not restaurant_names:
                    return CrossDatabaseResult(
                        success=True,
                        data=pd.DataFrame(),
                        error="Nenhum restaurante encontrado com os critérios especificados",
                        qdrant_filter_used=intent.menu_criteria,
                        restaurants_found=0,
                        execution_plan="Cross-database: No restaurants found"
                    )
                
                # Step 2: Generate filtered SQL for PostgreSQL
                filtered_sql = self._generate_filtered_sql(intent.financial_question, restaurant_names)
                
                # Step 3: Execute filtered SQL
                execution_result = self.vanna_converter.execute_query(filtered_sql)
                
                return CrossDatabaseResult(
                    success=execution_result["success"],
                    data=execution_result["result"],
                    error=execution_result["error"],
                    query=filtered_sql,
                    qdrant_filter_used=intent.menu_criteria,
                    restaurants_found=len(restaurant_names),
                    execution_plan=f"Cross-database: Qdrant({len(restaurant_names)} restaurants) → PostgreSQL"
                )
        
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return CrossDatabaseResult(
                success=False,
                error=str(e),
                execution_plan="Failed"
            )
    
    def train_model(self, question: str, sql: str) -> Dict[str, Any]:
        """Train the underlying Vanna model"""
        return self.vanna_converter.train_model(question, sql)
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about connected databases"""
        info = {
            "databases": {
                "postgresql": {"type": "Relational", "status": "connected"},
                "qdrant": {"type": "Vector", "status": "connected"}
            },
            "cross_database_patterns": [
                "restaurantes mexicanos + faturamento",
                "restaurantes vegetarianos + ticket médio", 
                "restaurantes com [critério] + análise financeira"
            ]
        }
        
        try:
            # Get PostgreSQL info from existing converter
            pg_info = self.vanna_converter.get_database_info()
            info["databases"]["postgresql"] = pg_info
        except:
            pass
        
        try:
            # Get Qdrant collections
            collections = self.qdrant_client.get_collections()
            info["databases"]["qdrant"]["collections"] = [c.name for c in collections.collections]
        except Exception as e:
            info["databases"]["qdrant"]["status"] = f"error: {e}"
        
        return info