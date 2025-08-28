"""
Advanced performance optimization layer for Vanna.ai system.
Includes semantic caching, query optimization, and intelligent model routing.
"""

import hashlib
import json
import pickle
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
import pandas as pd
import sqlite3
import threading
from collections import OrderedDict
import re

from config.advanced_features_config import EnhancementConfig, ModelType
from utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    query_hash: str
    original_question: str
    sql_query: str
    result_data: Any
    created_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    similarity_threshold: float = 0.0
    execution_time_ms: int = 0


@dataclass
class QueryMetrics:
    """Query performance metrics"""
    question: str
    sql_query: str
    execution_time_ms: int
    result_rows: int
    cache_hit: bool
    model_used: str
    tokens_used: int
    timestamp: datetime


class SemanticQueryCache:
    """Advanced semantic caching with similarity matching"""
    
    def __init__(self, config: EnhancementConfig):
        self.config = config
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.similarity_index: Dict[str, List[str]] = {}
        self.lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "total_queries": 0,
            "cache_size": 0
        }
        
        # Initialize persistent cache if configured
        self.db_path = "data/query_cache.db"
        self._init_persistent_cache()
    
    def _init_persistent_cache(self):
        """Initialize SQLite-based persistent cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS query_cache (
                        query_hash TEXT PRIMARY KEY,
                        original_question TEXT,
                        sql_query TEXT,
                        result_data BLOB,
                        created_at TIMESTAMP,
                        access_count INTEGER DEFAULT 0,
                        last_accessed TIMESTAMP,
                        similarity_threshold REAL DEFAULT 0.0,
                        execution_time_ms INTEGER DEFAULT 0
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_question_similarity 
                    ON query_cache(original_question)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created_at 
                    ON query_cache(created_at)
                """)
                
                conn.commit()
                logger.info("Persistent query cache initialized")
        except Exception as e:
            logger.error(f"Failed to initialize persistent cache: {e}")
    
    def _generate_query_hash(self, question: str, context: Dict[str, Any] = None) -> str:
        """Generate semantic hash for query"""
        # Normalize the question for better matching
        normalized = self._normalize_question(question)
        
        hash_input = normalized
        if context:
            hash_input += json.dumps(context, sort_keys=True)
        
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _normalize_question(self, question: str) -> str:
        """Normalize question for better semantic matching"""
        # Convert to lowercase
        normalized = question.lower().strip()
        
        # Remove common variations
        replacements = {
            "me mostre": "",
            "mostre": "",
            "quero ver": "", 
            "preciso": "",
            "gostaria": "",
            "por favor": "",
            "últimos": "ultimos",
            "último": "ultimo",
            "pagamentos": "pagamento",
            "transações": "transacao",
            "análise": "analise"
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _calculate_question_similarity(self, q1: str, q2: str) -> float:
        """Calculate semantic similarity between questions"""
        # Simple Jaccard similarity on normalized tokens
        tokens1 = set(self._normalize_question(q1).split())
        tokens2 = set(self._normalize_question(q2).split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        jaccard = intersection / union if union > 0 else 0.0
        
        # Boost similarity for exact keyword matches
        important_keywords = {'pix', 'cartao', 'boleto', 'pagamento', 'sucesso', 'falha', 'volume', 'taxa'}
        keyword_matches = len(tokens1.intersection(tokens2).intersection(important_keywords))
        keyword_boost = min(keyword_matches * 0.1, 0.3)
        
        return min(jaccard + keyword_boost, 1.0)
    
    def get_similar_cached_query(self, question: str, threshold: float = 0.7) -> Optional[CacheEntry]:
        """Find semantically similar cached query"""
        with self.lock:
            best_match = None
            best_similarity = 0.0
            
            for entry in self.cache.values():
                similarity = self._calculate_question_similarity(question, entry.original_question)
                
                if similarity >= threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = entry
                    best_match.similarity_threshold = similarity
            
            return best_match
    
    def get(self, question: str, context: Dict[str, Any] = None) -> Optional[CacheEntry]:
        """Get cached result with semantic matching"""
        # Try exact match first
        query_hash = self._generate_query_hash(question, context)
        
        with self.lock:
            if query_hash in self.cache:
                entry = self.cache[query_hash]
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                self._stats["hits"] += 1
                logger.debug(f"Cache hit (exact): {question[:50]}...")
                return entry
        
        # Try semantic similarity match
        similar_entry = self.get_similar_cached_query(question, threshold=0.75)
        if similar_entry:
            similar_entry.access_count += 1
            similar_entry.last_accessed = datetime.now()
            self._stats["hits"] += 1
            logger.info(f"Cache hit (semantic, {similar_entry.similarity_threshold:.2f}): {question[:50]}...")
            return similar_entry
        
        self._stats["misses"] += 1
        return None
    
    def put(self, question: str, sql_query: str, result_data: Any, 
            execution_time_ms: int = 0, context: Dict[str, Any] = None):
        """Cache query result"""
        query_hash = self._generate_query_hash(question, context)
        
        entry = CacheEntry(
            query_hash=query_hash,
            original_question=question,
            sql_query=sql_query,
            result_data=result_data,
            created_at=datetime.now(),
            execution_time_ms=execution_time_ms
        )
        
        with self.lock:
            # Add to memory cache
            self.cache[query_hash] = entry
            self._stats["cache_size"] = len(self.cache)
            
            # Enforce size limit
            if len(self.cache) > self.config.max_cache_entries:
                # Remove least recently used entries
                while len(self.cache) > self.config.max_cache_entries * 0.8:
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
            
            # Persist to database
            self._persist_entry(entry)
        
        logger.debug(f"Cached query: {question[:50]}... (hash: {query_hash})")
    
    def _persist_entry(self, entry: CacheEntry):
        """Persist cache entry to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO query_cache 
                    (query_hash, original_question, sql_query, result_data, 
                     created_at, access_count, last_accessed, similarity_threshold, execution_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.query_hash,
                    entry.original_question,
                    entry.sql_query,
                    pickle.dumps(entry.result_data),
                    entry.created_at,
                    entry.access_count,
                    entry.last_accessed,
                    entry.similarity_threshold,
                    entry.execution_time_ms
                ))
        except Exception as e:
            logger.warning(f"Failed to persist cache entry: {e}")
    
    def cleanup_expired(self):
        """Remove expired cache entries"""
        expiry_time = datetime.now() - timedelta(seconds=self.config.cache_ttl_seconds)
        
        with self.lock:
            expired_keys = []
            for key, entry in self.cache.items():
                if entry.created_at < expiry_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_queries = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_queries * 100) if total_queries > 0 else 0
            
            return {
                **self._stats,
                "hit_rate_percent": hit_rate,
                "total_queries": total_queries
            }
    
    def clear(self):
        """Clear cache"""
        with self.lock:
            self.cache.clear()
            self._stats = {"hits": 0, "misses": 0, "total_queries": 0, "cache_size": 0}


class IntelligentModelRouter:
    """Route queries to optimal AI models based on complexity and context"""
    
    def __init__(self, config: EnhancementConfig):
        self.config = config
        self.model_stats = {
            ModelType.FAST: {"queries": 0, "avg_time": 0, "success_rate": 0},
            ModelType.BALANCED: {"queries": 0, "avg_time": 0, "success_rate": 0},
            ModelType.PREMIUM: {"queries": 0, "avg_time": 0, "success_rate": 0}
        }
    
    def analyze_query_complexity(self, question: str, table_context: Dict = None) -> str:
        """Analyze query complexity to determine optimal model"""
        
        # Simple keyword-based complexity analysis
        complexity_indicators = {
            "simple": [
                "mostre", "me mostre", "liste", "dados", "total", "quantidade",
                "hoje", "ontem"
            ],
            "medium": [
                "compare", "analise", "análise", "vs", "entre", "últimos", "evolução",
                "taxa", "média", "grupo", "categoria"
            ],
            "complex": [
                "tendência", "padrão", "correlação", "previsão", "anomalia", "outlier",
                "sazonalidade", "cohort", "regressão", "otimização"
            ]
        }
        
        question_lower = question.lower()
        
        # Check for complex patterns
        complex_score = sum(1 for term in complexity_indicators["complex"] if term in question_lower)
        if complex_score >= 2:
            return "complex"
        
        # Check for medium complexity
        medium_score = sum(1 for term in complexity_indicators["medium"] if term in question_lower)
        if medium_score >= 2 or complex_score >= 1:
            return "medium"
        
        # Check table context complexity
        if table_context:
            table_count = len(table_context.get("related_tables", []))
            if table_count > 2:
                return "medium"
        
        return "simple"
    
    def select_model(self, question: str, table_context: Dict = None) -> ModelType:
        """Select optimal model based on query analysis"""
        
        if not self.config.enable_multi_model_routing:
            return ModelType.BALANCED  # Default fallback
        
        complexity = self.analyze_query_complexity(question, table_context)
        
        # Route based on complexity
        if complexity == "simple":
            return ModelType.FAST
        elif complexity == "medium":
            return ModelType.BALANCED
        else:
            return ModelType.PREMIUM
    
    def update_model_stats(self, model: ModelType, execution_time: float, success: bool):
        """Update model performance statistics"""
        stats = self.model_stats[model]
        stats["queries"] += 1
        
        # Update average execution time
        current_avg = stats["avg_time"]
        query_count = stats["queries"]
        stats["avg_time"] = (current_avg * (query_count - 1) + execution_time) / query_count
        
        # Update success rate
        current_successes = stats["success_rate"] * (query_count - 1)
        new_successes = current_successes + (1 if success else 0)
        stats["success_rate"] = new_successes / query_count
    
    def get_model_recommendations(self) -> Dict[str, Any]:
        """Get model usage recommendations"""
        recommendations = {}
        
        for model, stats in self.model_stats.items():
            if stats["queries"] > 10:  # Enough data for recommendations
                recommendations[model.value] = {
                    "efficiency": stats["success_rate"] / max(stats["avg_time"], 0.1),
                    "reliability": stats["success_rate"],
                    "performance": 1 / max(stats["avg_time"], 0.1),
                    "cost_efficiency": self._calculate_cost_efficiency(model, stats)
                }
        
        return recommendations
    
    def _calculate_cost_efficiency(self, model: ModelType, stats: Dict) -> float:
        """Calculate cost efficiency score for model"""
        # Cost per 1K tokens (approximate)
        cost_map = {
            ModelType.FAST: 0.002,
            ModelType.BALANCED: 0.03,
            ModelType.PREMIUM: 0.06
        }
        
        cost_per_token = cost_map[model]
        success_rate = stats["success_rate"]
        avg_time = stats["avg_time"]
        
        # Higher success rate and lower time = better efficiency
        efficiency = success_rate / (cost_per_token * max(avg_time, 0.1))
        return efficiency


class QueryOptimizer:
    """Optimize generated SQL queries for better performance"""
    
    def __init__(self):
        self.optimization_patterns = [
            self._add_limit_clause,
            self._optimize_date_filters,
            self._add_index_hints,
            self._optimize_aggregations,
            self._optimize_joins
        ]
    
    def optimize(self, sql_query: str, table_context: Dict = None) -> str:
        """Apply optimization patterns to SQL query"""
        optimized_sql = sql_query
        
        for optimizer in self.optimization_patterns:
            try:
                optimized_sql = optimizer(optimized_sql, table_context)
            except Exception as e:
                logger.warning(f"Query optimization failed: {e}")
                continue
        
        return optimized_sql
    
    def _add_limit_clause(self, sql: str, context: Dict = None) -> str:
        """Add LIMIT clause to prevent large result sets"""
        sql_upper = sql.upper()
        
        # Skip if already has LIMIT or is an aggregation query
        if "LIMIT" in sql_upper or any(agg in sql_upper for agg in ["COUNT(", "SUM(", "AVG(", "GROUP BY"]):
            return sql
        
        # Add reasonable limit
        return f"{sql.rstrip(';')} LIMIT 1000"
    
    def _optimize_date_filters(self, sql: str, context: Dict = None) -> str:
        """Optimize date-based filters"""
        # Add index hints for date columns
        date_columns = ["processed_at", "created_at", "invoice_date", "order_date"]
        
        for col in date_columns:
            if col in sql:
                # This would be database-specific optimization
                # For now, just ensure proper date formatting
                pass
        
        return sql
    
    def _add_index_hints(self, sql: str, context: Dict = None) -> str:
        """Add database index hints"""
        # PostgreSQL specific optimizations would go here
        # For now, return as-is
        return sql
    
    def _optimize_aggregations(self, sql: str, context: Dict = None) -> str:
        """Optimize aggregation queries"""
        # Could add HAVING clause optimizations
        # Or rewrite complex aggregations
        return sql
    
    def _optimize_joins(self, sql: str, context: Dict = None) -> str:
        """Optimize JOIN operations"""
        # Could analyze and reorder JOINs for better performance
        return sql


class PerformanceMonitor:
    """Monitor and analyze system performance"""
    
    def __init__(self):
        self.metrics: List[QueryMetrics] = []
        self.lock = threading.RLock()
    
    def record_query(self, metrics: QueryMetrics):
        """Record query performance metrics"""
        with self.lock:
            self.metrics.append(metrics)
            
            # Keep only recent metrics (last 1000 queries)
            if len(self.metrics) > 1000:
                self.metrics = self.metrics[-1000:]
    
    def get_performance_summary(self, last_n_queries: int = 100) -> Dict[str, Any]:
        """Get performance summary for recent queries"""
        with self.lock:
            recent_metrics = self.metrics[-last_n_queries:] if self.metrics else []
            
            if not recent_metrics:
                return {"error": "No metrics available"}
            
            total_time = sum(m.execution_time_ms for m in recent_metrics)
            cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
            
            return {
                "total_queries": len(recent_metrics),
                "avg_execution_time_ms": total_time / len(recent_metrics),
                "cache_hit_rate": cache_hits / len(recent_metrics) * 100,
                "avg_result_rows": sum(m.result_rows for m in recent_metrics) / len(recent_metrics),
                "model_distribution": self._get_model_distribution(recent_metrics),
                "slowest_queries": self._get_slowest_queries(recent_metrics, 5)
            }
    
    def _get_model_distribution(self, metrics: List[QueryMetrics]) -> Dict[str, int]:
        """Get distribution of model usage"""
        distribution = {}
        for m in metrics:
            distribution[m.model_used] = distribution.get(m.model_used, 0) + 1
        return distribution
    
    def _get_slowest_queries(self, metrics: List[QueryMetrics], top_n: int = 5) -> List[Dict]:
        """Get slowest queries for optimization"""
        sorted_metrics = sorted(metrics, key=lambda m: m.execution_time_ms, reverse=True)
        
        return [
            {
                "question": m.question[:100],
                "execution_time_ms": m.execution_time_ms,
                "result_rows": m.result_rows,
                "model_used": m.model_used
            }
            for m in sorted_metrics[:top_n]
        ]


# Global instances for shared use
_cache_instance: Optional[SemanticQueryCache] = None
_model_router_instance: Optional[IntelligentModelRouter] = None
_query_optimizer_instance: Optional[QueryOptimizer] = None
_performance_monitor_instance: Optional[PerformanceMonitor] = None


def get_semantic_cache(config: EnhancementConfig) -> SemanticQueryCache:
    """Get shared semantic cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticQueryCache(config)
    return _cache_instance


def get_model_router(config: EnhancementConfig) -> IntelligentModelRouter:
    """Get shared model router instance"""
    global _model_router_instance
    if _model_router_instance is None:
        _model_router_instance = IntelligentModelRouter(config)
    return _model_router_instance


def get_query_optimizer() -> QueryOptimizer:
    """Get shared query optimizer instance"""
    global _query_optimizer_instance
    if _query_optimizer_instance is None:
        _query_optimizer_instance = QueryOptimizer()
    return _query_optimizer_instance


def get_performance_monitor() -> PerformanceMonitor:
    """Get shared performance monitor instance"""
    global _performance_monitor_instance
    if _performance_monitor_instance is None:
        _performance_monitor_instance = PerformanceMonitor()
    return _performance_monitor_instance