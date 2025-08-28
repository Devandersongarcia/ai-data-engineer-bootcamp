"""
Intelligent Vanna converter with advanced AI features.
Integrates semantic caching, auto-insights, Brazilian context enhancement, and performance optimization.
"""

import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

from core.enhanced_vanna_converter import EnhancedVannaTextToSQLConverter
from config.advanced_features_config import (
    EnhancementConfig, FeatureLevel, AdvancedFeaturesConfig,
    get_config_by_level
)
from core.advanced_performance import (
    SemanticQueryCache, IntelligentModelRouter, QueryOptimizer,
    PerformanceMonitor, QueryMetrics,
    get_semantic_cache, get_model_router, get_query_optimizer, get_performance_monitor
)
from core.insights_engine import (
    PaymentInsightGenerator, VisualizationRecommendationEngine, QuerySuggestionEngine,
    BusinessInsight, VisualizationRecommendation,
    get_insight_generator, get_visualization_engine, get_suggestion_engine
)
from utils.logging_utils import get_logger

logger = get_logger(__name__)


class IntelligentVannaConverter(EnhancedVannaTextToSQLConverter):
    """
    Intelligent Vanna converter with advanced AI features.
    
    Provides zero-downtime migration path from basic to intelligent functionality
    while maintaining full backward compatibility.
    """
    
    def __init__(
        self,
        database_url: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        primary_table: Optional[str] = None,
        enhancement_level: str = "enhanced",
        auto_detect_schema: bool = True
    ):
        """
        Initialize intelligent converter with configurable enhancement level.
        
        Args:
            database_url: Database connection URL
            openai_api_key: OpenAI API key
            primary_table: Primary table to use
            enhancement_level: Level of enhancements ("basic", "enhanced", "advanced", "intelligent")
            auto_detect_schema: Whether to automatically detect schema
        """
        # Initialize base converter first
        super().__init__(
            database_url=database_url,
            openai_api_key=openai_api_key,
            primary_table=primary_table,
            auto_detect_schema=auto_detect_schema
        )
        
        # Setup advanced features
        self.enhancement_config = get_config_by_level(enhancement_level)
        self.features_config = AdvancedFeaturesConfig(self.enhancement_config)
        
        # Initialize advanced components
        self._setup_advanced_components()
        
        # Apply enhanced Brazilian context if enabled
        if self.features_config.should_enable_feature("brazilian_context"):
            self._apply_enhanced_context()
        
        logger.info(f"IntelligentVannaConverter initialized with {enhancement_level} features")
    
    def _setup_advanced_components(self):
        """Initialize advanced AI components"""
        try:
            # Semantic caching
            if self.features_config.should_enable_feature("semantic_caching"):
                self.semantic_cache = get_semantic_cache(self.enhancement_config)
                logger.info("Semantic caching enabled")
            else:
                self.semantic_cache = None
            
            # Model routing
            if self.features_config.should_enable_feature("multi_model_routing"):
                self.model_router = get_model_router(self.enhancement_config)
                logger.info("Multi-model routing enabled")
            else:
                self.model_router = None
            
            # Query optimization
            self.query_optimizer = get_query_optimizer()
            
            # Performance monitoring
            self.performance_monitor = get_performance_monitor()
            
            # Business intelligence components
            if self.features_config.should_enable_feature("auto_insights"):
                self.insight_generator = get_insight_generator()
                logger.info("Auto-insights enabled")
            else:
                self.insight_generator = None
            
            if self.features_config.should_enable_feature("visualization_recommendations"):
                self.visualization_engine = get_visualization_engine()
                logger.info("Visualization recommendations enabled")
            else:
                self.visualization_engine = None
            
            if self.features_config.should_enable_feature("query_suggestions"):
                self.suggestion_engine = get_suggestion_engine()
                logger.info("Query suggestions enabled")
            else:
                self.suggestion_engine = None
                
        except Exception as e:
            logger.error(f"Failed to setup advanced components: {e}")
            # Gracefully degrade to basic functionality
            self.semantic_cache = None
            self.model_router = None
            self.insight_generator = None
    
    def _apply_enhanced_context(self):
        """Apply enhanced Brazilian payment context"""
        try:
            enhanced_context = self.features_config.get_enhanced_context()
            
            # Train with enhanced context
            self.vn.train(documentation=enhanced_context)
            
            # Apply enhanced Portuguese mappings
            portuguese_mappings = self.features_config.get_portuguese_mappings()
            self.log_info(f"Applied {len(portuguese_mappings)} enhanced Portuguese mappings")
            
        except Exception as e:
            logger.warning(f"Failed to apply enhanced context: {e}")
    
    def convert_to_sql(self, user_question: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Enhanced SQL conversion with semantic caching and model routing.
        Maintains backward compatibility while adding advanced features.
        """
        start_time = time.time()
        model_used = "gpt-3.5-turbo"  # Default fallback
        cache_hit = False
        
        try:
            # Try semantic cache first
            if self.semantic_cache and use_cache:
                cached_entry = self.semantic_cache.get(user_question)
                if cached_entry:
                    cache_hit = True
                    execution_time = int((time.time() - start_time) * 1000)
                    
                    # Record performance metrics
                    self._record_query_metrics(
                        user_question, cached_entry.sql_query, execution_time,
                        0, cache_hit, "cached", 0
                    )
                    
                    self.log_info(f"Cache hit for question: {user_question[:50]}...")
                    return {
                        "success": True,
                        "error": None,
                        "sql_query": cached_entry.sql_query,
                        "result": None,
                        "cached": True,
                        "similarity": getattr(cached_entry, 'similarity_threshold', 1.0)
                    }
            
            # Select optimal model if routing is enabled
            if self.model_router:
                model_type = self.model_router.select_model(user_question, {
                    "primary_table": self.primary_table,
                    "related_tables": ["orders", "users", "payments"]
                })
                model_used = model_type.value
                
                # Update Vanna model if different from current
                current_model = getattr(self.vn, '_model', 'gpt-3.5-turbo')
                if model_used != current_model:
                    self.vn._model = model_used
                    logger.debug(f"Switched to model: {model_used}")
            
            # Use enhanced parent conversion
            result = super().convert_to_sql(user_question, use_cache=False)  # Skip base cache
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Cache successful results
            if result["success"] and self.semantic_cache:
                self.semantic_cache.put(
                    user_question, 
                    result["sql_query"], 
                    result,
                    execution_time
                )
            
            # Apply query optimization
            if result["success"] and result["sql_query"]:
                optimized_sql = self.query_optimizer.optimize(result["sql_query"], {
                    "primary_table": self.primary_table,
                    "question_context": user_question
                })
                
                if optimized_sql != result["sql_query"]:
                    result["sql_query"] = optimized_sql
                    result["optimized"] = True
                    logger.debug("Applied query optimization")
            
            # Record performance metrics
            self._record_query_metrics(
                user_question, result.get("sql_query", ""), execution_time,
                0, cache_hit, model_used, 0
            )
            
            # Update model statistics if routing enabled
            if self.model_router:
                self.model_router.update_model_stats(
                    self.model_router.select_model(user_question),
                    execution_time / 1000.0,
                    result["success"]
                )
            
            return result
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self._record_query_metrics(
                user_question, "", execution_time, 0, cache_hit, model_used, 0
            )
            
            logger.error(f"Enhanced SQL conversion failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "sql_query": None,
                "result": None
            }
    
    def process_question_with_intelligence(self, user_question: str, 
                                          generate_insights: bool = None,
                                          suggest_visualizations: bool = None,
                                          suggest_followups: bool = None) -> Dict[str, Any]:
        """
        Complete intelligent processing with auto-insights, visualizations, and suggestions.
        
        This is the main enhanced method that provides full AI capabilities.
        """
        # Use feature configuration defaults if not specified
        if generate_insights is None:
            generate_insights = self.features_config.should_enable_feature("auto_insights")
        if suggest_visualizations is None:
            suggest_visualizations = self.features_config.should_enable_feature("visualization_recommendations")
        if suggest_followups is None:
            suggest_followups = self.features_config.should_enable_feature("query_suggestions")
        
        self.log_info(f"Processing question with intelligence: {user_question[:50]}...", {
            "insights_enabled": generate_insights,
            "visualizations_enabled": suggest_visualizations,
            "suggestions_enabled": suggest_followups
        })
        
        # Process basic question
        result = self.process_question(user_question)
        
        if not result["success"]:
            return result
        
        # Enhanced result with intelligence features
        enhanced_result = {
            **result,
            "intelligence": {
                "insights": [],
                "visualizations": [],
                "suggestions": [],
                "performance": {}
            }
        }
        
        try:
            df = result.get("result")
            if df is not None and not df.empty:
                
                # Generate business insights
                if generate_insights and self.insight_generator:
                    insights = self.insight_generator.generate_insights(
                        df, user_question, self.primary_table
                    )
                    enhanced_result["intelligence"]["insights"] = [
                        {
                            "type": insight.insight_type,
                            "title": insight.title,
                            "description": insight.description,
                            "severity": insight.severity,
                            "confidence": insight.confidence,
                            "recommendations": insight.recommendations
                        }
                        for insight in insights
                    ]
                    self.log_info(f"Generated {len(insights)} business insights")
                
                # Generate visualization recommendations
                if suggest_visualizations and self.visualization_engine:
                    viz_recommendations = self.visualization_engine.recommend_visualizations(
                        df, user_question, insights if generate_insights else []
                    )
                    enhanced_result["intelligence"]["visualizations"] = [
                        {
                            "chart_type": viz.chart_type,
                            "title": viz.title,
                            "description": viz.description,
                            "config": viz.config,
                            "priority": viz.priority,
                            "rationale": viz.rationale
                        }
                        for viz in viz_recommendations
                    ]
                    self.log_info(f"Generated {len(viz_recommendations)} visualization recommendations")
                
                # Generate follow-up suggestions
                if suggest_followups and self.suggestion_engine:
                    suggestions = self.suggestion_engine.suggest_followup_questions(
                        df, user_question, insights if generate_insights else []
                    )
                    enhanced_result["intelligence"]["suggestions"] = suggestions
                    self.log_info(f"Generated {len(suggestions)} follow-up suggestions")
            
            # Add performance information
            if self.semantic_cache:
                cache_stats = self.semantic_cache.get_stats()
                enhanced_result["intelligence"]["performance"]["cache"] = cache_stats
            
            if self.performance_monitor:
                perf_summary = self.performance_monitor.get_performance_summary(50)
                enhanced_result["intelligence"]["performance"]["system"] = perf_summary
            
        except Exception as e:
            logger.warning(f"Intelligence features failed: {e}")
            # Continue with basic result even if intelligence fails
        
        return enhanced_result
    
    def _record_query_metrics(self, question: str, sql_query: str, execution_time_ms: int,
                             result_rows: int, cache_hit: bool, model_used: str, tokens_used: int):
        """Record query performance metrics"""
        try:
            metrics = QueryMetrics(
                question=question,
                sql_query=sql_query,
                execution_time_ms=execution_time_ms,
                result_rows=result_rows,
                cache_hit=cache_hit,
                model_used=model_used,
                tokens_used=tokens_used,
                timestamp=datetime.now()
            )
            
            if self.performance_monitor:
                self.performance_monitor.record_query(metrics)
                
        except Exception as e:
            logger.warning(f"Failed to record metrics: {e}")
    
    def get_intelligence_summary(self) -> Dict[str, Any]:
        """Get summary of intelligence features and their performance"""
        summary = {
            "enhancement_level": self.enhancement_config.feature_level.value,
            "enabled_features": [],
            "performance": {},
            "statistics": {}
        }
        
        # List enabled features
        feature_checks = [
            ("brazilian_context", "Enhanced Brazilian Payment Context"),
            ("semantic_caching", "Semantic Query Caching"), 
            ("auto_insights", "Business Intelligence Insights"),
            ("query_suggestions", "Smart Query Suggestions"),
            ("visualization_recommendations", "Visualization Recommendations"),
            ("multi_model_routing", "Intelligent Model Routing"),
            ("anomaly_detection", "Anomaly Detection")
        ]
        
        for feature_key, feature_name in feature_checks:
            if self.features_config.should_enable_feature(feature_key):
                summary["enabled_features"].append(feature_name)
        
        # Performance statistics
        if self.semantic_cache:
            summary["performance"]["cache"] = self.semantic_cache.get_stats()
        
        if self.performance_monitor:
            summary["performance"]["queries"] = self.performance_monitor.get_performance_summary()
        
        if self.model_router:
            summary["performance"]["models"] = self.model_router.get_model_recommendations()
        
        return summary
    
    def migrate_to_level(self, new_level: str) -> Dict[str, Any]:
        """
        Migrate to a different enhancement level at runtime.
        Provides zero-downtime feature upgrades/downgrades.
        """
        try:
            old_level = self.enhancement_config.feature_level.value
            
            # Create new configuration
            new_config = get_config_by_level(new_level)
            self.enhancement_config = new_config
            self.features_config = AdvancedFeaturesConfig(new_config)
            
            # Reinitialize components based on new level
            self._setup_advanced_components()
            
            if self.features_config.should_enable_feature("brazilian_context"):
                self._apply_enhanced_context()
            
            logger.info(f"Successfully migrated from {old_level} to {new_level}")
            
            return {
                "success": True,
                "message": f"Migrated from {old_level} to {new_level}",
                "old_level": old_level,
                "new_level": new_level,
                "enabled_features": [f for f in self.get_intelligence_summary()["enabled_features"]]
            }
            
        except Exception as e:
            logger.error(f"Migration to {new_level} failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "current_level": self.enhancement_config.feature_level.value
            }
    
    def cleanup_resources(self):
        """Clean up resources and perform maintenance"""
        try:
            if self.semantic_cache:
                self.semantic_cache.cleanup_expired()
                logger.info("Cache cleanup completed")
            
        except Exception as e:
            logger.warning(f"Resource cleanup failed: {e}")
    
    # Backward compatibility methods
    def process_question(self, user_question: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Backward compatible method that uses intelligent features when available.
        Falls back to basic functionality if intelligence features fail.
        """
        try:
            # Try intelligent processing first if features are available
            if (self.features_config.should_enable_feature("auto_insights") or 
                self.features_config.should_enable_feature("visualization_recommendations")):
                
                return self.process_question_with_intelligence(user_question, 
                                                              generate_insights=True,
                                                              suggest_visualizations=False,
                                                              suggest_followups=False)
            
        except Exception as e:
            logger.warning(f"Intelligent processing failed, falling back to basic: {e}")
        
        # Fallback to parent implementation
        return super().process_question(user_question, use_cache)


# Convenience factory functions for different levels
def create_basic_intelligent_converter(**kwargs) -> IntelligentVannaConverter:
    """Create converter with basic enhancements"""
    return IntelligentVannaConverter(enhancement_level="basic", **kwargs)


def create_enhanced_intelligent_converter(**kwargs) -> IntelligentVannaConverter:
    """Create converter with enhanced features (recommended)"""
    return IntelligentVannaConverter(enhancement_level="enhanced", **kwargs)


def create_advanced_intelligent_converter(**kwargs) -> IntelligentVannaConverter:
    """Create converter with advanced features"""
    return IntelligentVannaConverter(enhancement_level="advanced", **kwargs)


def create_intelligent_payments_converter(**kwargs) -> IntelligentVannaConverter:
    """Create intelligent converter optimized for payments table"""
    return IntelligentVannaConverter(
        primary_table="payments",
        enhancement_level="enhanced",
        **kwargs
    )


# Backward compatibility - maintain existing interface
VannaIntelligentConverter = IntelligentVannaConverter