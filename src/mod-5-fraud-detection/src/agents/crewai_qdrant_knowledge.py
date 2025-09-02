"""
CrewAI Qdrant Knowledge Base Integration for Fraud Detection
Connects to rag_fraud_analysis collection for enhanced RAG capabilities
"""

import logging
import time
import os
from typing import Dict, List, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, PointStruct
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class CrewAIQdrantKnowledge:
    """Qdrant integration optimized for CrewAI agents with fraud detection knowledge"""
    
    def __init__(self, 
                 qdrant_url: Optional[str] = None,
                 collection_name: Optional[str] = None,
                 api_key: Optional[str] = None):
        """
        Initialize Qdrant client for CrewAI agents using environment variables
        
        Args:
            qdrant_url: Qdrant instance URL (defaults to QDRANT_URL env var)
            collection_name: Collection name (defaults to QDRANT_COLLECTION_NAME env var)
            api_key: API key for authentication (defaults to QDRANT_API_KEY env var)
        """
        self.qdrant_url = qdrant_url or os.getenv('QDRANT_URL', 'http://localhost:6333')
        self.collection_name = collection_name or os.getenv('QDRANT_COLLECTION_NAME', 'rag_fraud_analysis')
        self.api_key = api_key or os.getenv('QDRANT_API_KEY')
        
        self.client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.api_key
        )
        
        # Knowledge cache for performance
        self.knowledge_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Initialize connection and verify collection
        self._verify_collection()
        
        logger.info(f"CrewAI Qdrant Knowledge initialized - URL: {self.qdrant_url}, Collection: {self.collection_name}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Qdrant connection and return health status"""
        try:
            # Test basic connection
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            # Check if our collection exists
            collection_exists = self.collection_name in collection_names
            
            result = {
                "success": True,
                "url": self.qdrant_url,
                "collections": collection_names,
                "target_collection": self.collection_name,
                "collection_exists": collection_exists
            }
            
            if collection_exists:
                # Get collection details
                collection_info = self.client.get_collection(self.collection_name)
                result["points_count"] = collection_info.points_count
                result["status"] = "healthy"
            else:
                result["status"] = "collection_missing"
                result["error"] = f"Collection '{self.collection_name}' not found"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": self.qdrant_url,
                "status": "connection_failed"
            }
    
    def _verify_collection(self):
        """Verify that the rag_fraud_analysis collection exists"""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.warning(f"Collection '{self.collection_name}' not found. Available: {collection_names}")
                return False
            
            # Get collection info
            collection_info = self.client.get_collection(self.collection_name)
            logger.info(f"Connected to collection: {self.collection_name} ({collection_info.points_count} points)")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying Qdrant collection: {e}")
            return False
    
    def search_fraud_knowledge(self, 
                              query_text: str,
                              fraud_types: Optional[List[str]] = None,
                              limit: int = 5,
                              score_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Search fraud detection knowledge in Qdrant collection
        
        Args:
            query_text: Search query
            fraud_types: Optional filter by fraud types
            limit: Maximum results to return
            score_threshold: Minimum similarity score
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            # Check cache first
            cache_key = f"{query_text}_{fraud_types}_{limit}_{score_threshold}"
            if cache_key in self.knowledge_cache:
                cached_item = self.knowledge_cache[cache_key]
                if cached_item['expires'] > time.time():
                    return cached_item['data']
            
            # Note: Removing fraud_type filtering since collection doesn't have proper indexes
            # Will rely on text-based search and post-filtering instead
            search_filters = None
            
            # Perform vector search (assuming you have embeddings)
            # Note: This requires the query to be embedded first
            # For now, we'll do a text-based search on metadata
            search_results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=search_filters,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # Process results
            knowledge_points = []
            for point in search_results[0]:  # scroll returns (points, next_page_offset)
                payload = point.payload or {}
                
                # Extract relevant information matching your Qdrant data structure
                knowledge_point = {
                    "id": point.id,
                    "content": payload.get("content", payload.get("text", "")),
                    "fraud_type": payload.get("fraud_type", "general"),
                    "fraud_score": payload.get("fraud_score", payload.get("confidence", 0.5)),
                    "recommended_action": payload.get("recommended_action", "MONITOR"),
                    "source": payload.get("source", "unknown"),
                    "timestamp": payload.get("timestamp"),
                    "metadata": payload.get("metadata", {})
                }
                
                # Post-filter by fraud type if specified
                if fraud_types and knowledge_point['fraud_type'] not in fraud_types:
                    continue
                
                # Filter by relevance (simple text matching for now)
                if self._is_relevant(query_text, knowledge_point['content']):
                    knowledge_points.append(knowledge_point)
            
            # Sort by fraud_score (matching your Qdrant data structure)
            knowledge_points.sort(key=lambda x: x['fraud_score'], reverse=True)
            knowledge_points = knowledge_points[:limit]
            
            result = {
                "success": True,
                "query": query_text,
                "total_found": len(knowledge_points),
                "knowledge_points": knowledge_points,
                "search_metadata": {
                    "fraud_types_filter": fraud_types,
                    "score_threshold": score_threshold,
                    "collection": self.collection_name
                }
            }
            
            # Cache result
            self.knowledge_cache[cache_key] = {
                'data': result,
                'expires': time.time() + self.cache_ttl
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching fraud knowledge: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query_text,
                "knowledge_points": []
            }
    
    def _is_relevant(self, query: str, content: str) -> bool:
        """Simple relevance check based on keyword matching"""
        query_words = query.lower().split()
        content_lower = content.lower()
        
        # Count matching words
        matches = sum(1 for word in query_words if word in content_lower)
        relevance_score = matches / len(query_words) if query_words else 0
        
        return relevance_score >= 0.3  # At least 30% word overlap
    
    def get_fraud_patterns(self, fraud_type: str) -> Dict[str, Any]:
        """
        Get specific fraud patterns for a given fraud type
        
        Args:
            fraud_type: Type of fraud to search for
            
        Returns:
            Dictionary with fraud patterns and indicators
        """
        try:
            # Search for specific fraud type patterns
            result = self.search_fraud_knowledge(
                query_text=f"fraud patterns {fraud_type}",
                fraud_types=[fraud_type],
                limit=10
            )
            
            if result["success"]:
                patterns = []
                for point in result["knowledge_points"]:
                    pattern = {
                        "type": fraud_type,
                        "description": point["content"],
                        "confidence": point["confidence"],
                        "indicators": point["metadata"].get("indicators", []),
                        "thresholds": point["metadata"].get("thresholds", {}),
                        "source": point["source"]
                    }
                    patterns.append(pattern)
                
                return {
                    "success": True,
                    "fraud_type": fraud_type,
                    "patterns": patterns,
                    "total_patterns": len(patterns)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting fraud patterns for {fraud_type}: {e}")
            return {
                "success": False,
                "error": str(e),
                "fraud_type": fraud_type,
                "patterns": []
            }
    
    def get_similar_cases(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find similar historical fraud cases
        
        Args:
            order_data: Current order information
            
        Returns:
            Dictionary with similar cases and their outcomes
        """
        try:
            # Create search query based on order characteristics
            amount = order_data.get('total_amount', 0)
            payment_method = order_data.get('payment_method', '')
            account_age = order_data.get('account_age_days', 0)
            
            query = f"order amount {amount} payment {payment_method} account age {account_age}"
            
            result = self.search_fraud_knowledge(
                query_text=query,
                limit=5,
                score_threshold=0.6
            )
            
            if result["success"]:
                similar_cases = []
                for point in result["knowledge_points"]:
                    case = {
                        "case_id": point["id"],
                        "description": point["content"],
                        "fraud_type": point.get("fraud_type", "unknown"),
                        "outcome": point.get("metadata", {}).get("outcome", "unknown"),
                        "confidence": point.get("confidence", point.get("fraud_score", 0.5)),
                        "similarity_factors": self._extract_similarity_factors(
                            order_data, point["metadata"]
                        )
                    }
                    similar_cases.append(case)
                
                return {
                    "success": True,
                    "current_order": order_data.get('order_id', 'unknown'),
                    "similar_cases": similar_cases,
                    "total_found": len(similar_cases)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error finding similar cases: {e}")
            return {
                "success": False,
                "error": str(e),
                "similar_cases": []
            }
    
    def _extract_similarity_factors(self, current_order: Dict, case_metadata: Dict) -> List[str]:
        """Extract what makes cases similar"""
        factors = []
        
        # Amount similarity
        current_amount = current_order.get('total_amount', 0)
        case_amount = case_metadata.get('order_amount', 0)
        if abs(current_amount - case_amount) / max(current_amount, case_amount, 1) < 0.2:
            factors.append(f"Similar amount (~${case_amount})")
        
        # Payment method match
        if current_order.get('payment_method') == case_metadata.get('payment_method'):
            factors.append(f"Same payment method")
        
        # Account age similarity
        current_age = current_order.get('account_age_days', 0)
        case_age = case_metadata.get('account_age_days', 0)
        if abs(current_age - case_age) < 7:
            factors.append(f"Similar account age")
        
        return factors
    
    def add_fraud_case(self, 
                      case_data: Dict[str, Any],
                      embedding: Optional[List[float]] = None) -> bool:
        """
        Add a new fraud case to the knowledge base
        
        Args:
            case_data: Fraud case information
            embedding: Optional vector embedding
            
        Returns:
            Boolean indicating success
        """
        try:
            # Create point for insertion
            point_id = case_data.get('case_id', f"case_{int(time.time())}")
            
            # Prepare payload
            payload = {
                "content": case_data.get('description', ''),
                "fraud_type": case_data.get('fraud_type', 'general'),
                "confidence": case_data.get('confidence', 0.5),
                "source": case_data.get('source', 'system'),
                "timestamp": case_data.get('timestamp', time.time()),
                "metadata": case_data.get('metadata', {}),
                "outcome": case_data.get('outcome', 'unknown'),
                "order_amount": case_data.get('order_amount', 0),
                "payment_method": case_data.get('payment_method', ''),
                "account_age_days": case_data.get('account_age_days', 0)
            }
            
            # Create point
            if embedding:
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            else:
                # If no embedding provided, create a dummy vector
                # In production, you'd generate proper embeddings
                dummy_vector = [0.0] * 768  # Common embedding dimension
                point = PointStruct(
                    id=point_id,
                    vector=dummy_vector,
                    payload=payload
                )
            
            # Insert point
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Added fraud case to knowledge base: {point_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding fraud case: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the fraud knowledge collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            # Get point count by fraud type
            fraud_type_counts = {}
            
            # Scroll through all points to get fraud type distribution
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,  # Large limit to get all points
                with_payload=True,
                with_vectors=False
            )
            
            for point in scroll_result[0]:
                fraud_type = point.payload.get('fraud_type', 'unknown')
                fraud_type_counts[fraud_type] = fraud_type_counts.get(fraud_type, 0) + 1
            
            return {
                "collection_name": self.collection_name,
                "total_points": collection_info.points_count,
                "vector_size": collection_info.config.params.vectors.size,
                "fraud_type_distribution": fraud_type_counts,
                "status": collection_info.status.value
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                "error": str(e),
                "collection_name": self.collection_name
            }

# CrewAI Tool Integration
class QdrantKnowledgeTool:
    """CrewAI-compatible tool for accessing Qdrant fraud knowledge"""
    
    def __init__(self, qdrant_knowledge: CrewAIQdrantKnowledge):
        self.knowledge = qdrant_knowledge
        # Create the tool function
        self.search_fraud_knowledge = self._create_search_tool()
    
    def _create_search_tool(self):
        """Create a tool function for CrewAI"""
        def search_fraud_knowledge(query: str) -> str:
            """
            Search for fraud detection patterns and knowledge from historical data.
            
            Args:
                query: Search query for fraud patterns, cases, or knowledge
                
            Returns:
                Formatted string with fraud knowledge
            """
            return self._search_knowledge(query)
        
        # Add tool metadata
        search_fraud_knowledge.__name__ = "search_fraud_knowledge"
        search_fraud_knowledge.description = "Search for fraud detection patterns and knowledge from historical data"
        return search_fraud_knowledge
    
    def _search_knowledge(self, query: str) -> str:
        """
        Search fraud detection knowledge
        
        Args:
            query: Search query for fraud patterns
            
        Returns:
            Formatted knowledge search results
        """
        
        result = self.knowledge.search_fraud_knowledge(
            query_text=query,
            fraud_types=None,
            limit=5
        )
        
        if result["success"]:
            formatted_results = []
            for point in result["knowledge_points"]:
                formatted_results.append(f"""
                📊 **Fraud Knowledge Point**
                - Type: {point['fraud_type']}
                - Confidence: {point['confidence']:.2f}
                - Content: {point['content'][:200]}...
                - Source: {point['source']}
                """)
            
            return f"""
            🔍 **Fraud Knowledge Search Results**
            Query: {query}
            Total Found: {result['total_found']}
            
            {chr(10).join(formatted_results)}
            """
        else:
            return f"❌ Knowledge search failed: {result.get('error', 'Unknown error')}"
    
    def get_fraud_patterns(self, fraud_type: str) -> str:
        """
        Get specific fraud patterns for analysis
        
        Args:
            fraud_type: Type of fraud to analyze
            
        Returns:
            Formatted fraud patterns and indicators
        """
        result = self.knowledge.get_fraud_patterns(fraud_type)
        
        if result["success"]:
            patterns_text = []
            for pattern in result["patterns"]:
                patterns_text.append(f"""
                🚨 **{fraud_type.upper()} Pattern**
                - Description: {pattern['description'][:150]}...
                - Confidence: {pattern['confidence']:.2f}
                - Indicators: {', '.join(pattern['indicators'][:3])}
                - Source: {pattern['source']}
                """)
            
            return f"""
            📋 **Fraud Patterns for {fraud_type}**
            Total Patterns: {result['total_patterns']}
            
            {chr(10).join(patterns_text)}
            """
        else:
            return f"❌ Pattern search failed for {fraud_type}: {result.get('error', 'Unknown error')}"
    
    def find_similar_cases(self, order_data_json: str) -> str:
        """
        Find similar historical fraud cases
        
        Args:
            order_data_json: JSON string with order data
            
        Returns:
            Formatted similar cases
        """
        try:
            order_data = json.loads(order_data_json)
        except:
            order_data = {"order_id": "unknown", "total_amount": 0}
        
        result = self.knowledge.get_similar_cases(order_data)
        
        if result["success"]:
            cases_text = []
            for case in result["similar_cases"]:
                cases_text.append(f"""
                📝 **Similar Case**
                - Case ID: {case['case_id']}
                - Fraud Type: {case['fraud_type']}
                - Outcome: {case['outcome']}
                - Confidence: {case['confidence']:.2f}
                - Similarity: {', '.join(case['similarity_factors'])}
                """)
            
            return f"""
            🔍 **Similar Historical Cases**
            Current Order: {result['current_order']}
            Total Found: {result['total_found']}
            
            {chr(10).join(cases_text)}
            """
        else:
            return f"❌ Similar case search failed: {result.get('error', 'Unknown error')}"