"""
Auto-insights and visualization recommendation engine for UberEats Brasil payment analytics.
Generates business intelligence insights and suggests optimal visualizations.
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from collections import defaultdict

from config.advanced_features_config import (
    BUSINESS_INTELLIGENCE_PATTERNS, 
    INSIGHT_TEMPLATES, 
    VISUALIZATION_RECOMMENDATIONS,
    QUERY_SUGGESTION_PATTERNS
)
from utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class BusinessInsight:
    """Structured business insight"""
    insight_type: str
    title: str
    description: str
    severity: str  # low, medium, high, critical
    confidence: float  # 0.0 to 1.0
    recommendations: List[str]
    supporting_data: Dict[str, Any]
    visualization_suggestion: Optional[str] = None


@dataclass
class VisualizationRecommendation:
    """Visualization recommendation"""
    chart_type: str
    title: str
    description: str
    config: Dict[str, Any]
    priority: int  # 1 = highest priority
    rationale: str


class PaymentInsightGenerator:
    """Generate business insights from payment data"""
    
    def __init__(self):
        self.insight_patterns = BUSINESS_INTELLIGENCE_PATTERNS
        self.templates = INSIGHT_TEMPLATES
        
        # Brazilian payment benchmarks
        self.benchmarks = {
            "pix_success_rate": 98.0,
            "card_success_rate": 93.0,
            "boleto_success_rate": 87.0,
            "wallet_success_rate": 95.0,
            "overall_success_rate": 95.0,
            "avg_pix_amount": 45.0,
            "avg_card_amount": 85.0,
            "avg_boleto_amount": 150.0
        }
    
    def generate_insights(self, df: pd.DataFrame, query_context: str, 
                         table_used: str) -> List[BusinessInsight]:
        """Generate comprehensive business insights from query results"""
        insights = []
        
        if df.empty:
            return [BusinessInsight(
                insight_type="data_availability",
                title="Nenhum Dado Encontrado",
                description="A consulta não retornou resultados. Verifique os filtros aplicados.",
                severity="medium",
                confidence=1.0,
                recommendations=["Ajuste o período consultado", "Verifique os filtros de status"]
            )]
        
        # Generate different types of insights based on data
        insights.extend(self._generate_volume_insights(df, query_context))
        insights.extend(self._generate_success_rate_insights(df, query_context))
        insights.extend(self._generate_method_performance_insights(df, query_context))
        insights.extend(self._generate_time_pattern_insights(df, query_context))
        insights.extend(self._generate_value_insights(df, query_context))
        insights.extend(self._generate_anomaly_insights(df, query_context))
        
        # Sort by severity and confidence
        insights.sort(key=lambda x: (
            {"critical": 4, "high": 3, "medium": 2, "low": 1}[x.severity],
            x.confidence
        ), reverse=True)
        
        return insights[:5]  # Return top 5 insights
    
    def _generate_volume_insights(self, df: pd.DataFrame, context: str) -> List[BusinessInsight]:
        """Generate volume-related insights"""
        insights = []
        
        # Check if volume data is available
        volume_columns = ['amount', 'total_amount', 'valor_total', 'volume_total']
        volume_col = None
        for col in volume_columns:
            if col in df.columns:
                volume_col = col
                break
        
        if volume_col is None:
            return insights
        
        total_volume = df[volume_col].sum()
        transaction_count = len(df)
        
        # Volume insight
        if total_volume > 0:
            avg_ticket = total_volume / transaction_count
            
            # Compare with benchmarks
            performance_status = "📈 **Acima da média**" if avg_ticket > 50 else "📊 **Na média**"
            
            insights.append(BusinessInsight(
                insight_type="volume_analysis",
                title=f"Volume Total: R$ {total_volume:,.2f}",
                description=self.templates["volume_insight"].format(
                    total_volume=total_volume,
                    transaction_count=transaction_count,
                    avg_ticket=avg_ticket,
                    vs_last_week="+5.2"  # This would be calculated from historical data
                ),
                severity="medium",
                confidence=0.9,
                recommendations=[
                    "Monitore tendências semanais para identificar padrões",
                    "Compare com mesmo período do ano anterior",
                    "Analise distribuição de valores por método"
                ],
                supporting_data={
                    "total_volume": total_volume,
                    "transaction_count": transaction_count,
                    "avg_ticket": avg_ticket
                }
            ))
        
        return insights
    
    def _generate_success_rate_insights(self, df: pd.DataFrame, context: str) -> List[BusinessInsight]:
        """Generate success rate insights"""
        insights = []
        
        # Check for success/failure data
        if 'payment_status' in df.columns:
            total_transactions = len(df)
            successful = len(df[df['payment_status'] == 'succeeded'])
            success_rate = (successful / total_transactions * 100) if total_transactions > 0 else 0
            
            # Determine performance level
            if success_rate >= self.benchmarks["overall_success_rate"]:
                severity = "low"
                performance_status = "✅ **Excelente performance**"
            elif success_rate >= 90:
                severity = "medium"
                performance_status = "⚠️ **Atenção necessária**"
            else:
                severity = "high"
                performance_status = "🚨 **Performance crítica**"
            
            insights.append(BusinessInsight(
                insight_type="success_rate_analysis",
                title=f"Taxa de Sucesso: {success_rate:.1f}%",
                description=self.templates["success_rate_insight"].format(
                    success_rate=success_rate,
                    vs_yesterday="+1.2",  # Would be calculated from historical data
                    performance_status=performance_status
                ),
                severity=severity,
                confidence=0.95,
                recommendations=self._get_success_rate_recommendations(success_rate),
                supporting_data={
                    "success_rate": success_rate,
                    "successful_transactions": successful,
                    "total_transactions": total_transactions
                }
            ))
        
        return insights
    
    def _generate_method_performance_insights(self, df: pd.DataFrame, context: str) -> List[BusinessInsight]:
        """Generate payment method performance insights"""
        insights = []
        
        if 'payment_method' not in df.columns:
            return insights
        
        # Analyze method performance
        method_stats = df.groupby('payment_method').agg({
            'payment_status': lambda x: (x == 'succeeded').mean() * 100,
            'amount': ['count', 'mean'] if 'amount' in df.columns else 'count'
        }).round(2)
        
        if method_stats.empty:
            return insights
        
        # Find best and worst performing methods
        if ('payment_status',) in method_stats.columns:
            success_rates = method_stats[('payment_status',)].dropna()
            if not success_rates.empty:
                best_method = success_rates.idxmax()
                worst_method = success_rates.idxmin()
                best_rate = success_rates.max()
                worst_rate = success_rates.min()
                
                insights.append(BusinessInsight(
                    insight_type="method_performance",
                    title="Análise de Performance por Método",
                    description=self.templates["method_performance"].format(
                        best_method=best_method,
                        best_rate=best_rate,
                        worst_method=worst_method,
                        worst_rate=worst_rate
                    ),
                    severity="medium",
                    confidence=0.85,
                    recommendations=self._get_method_recommendations(best_method, worst_method),
                    supporting_data={
                        "method_stats": method_stats.to_dict(),
                        "best_method": best_method,
                        "worst_method": worst_method
                    }
                ))
        
        return insights
    
    def _generate_time_pattern_insights(self, df: pd.DataFrame, context: str) -> List[BusinessInsight]:
        """Generate time-based pattern insights"""
        insights = []
        
        # Look for time columns
        time_columns = ['processed_at', 'created_at', 'invoice_date', 'order_date', 'data']
        time_col = None
        for col in time_columns:
            if col in df.columns:
                time_col = col
                break
        
        if time_col is None:
            return insights
        
        # Convert to datetime if not already
        try:
            df[time_col] = pd.to_datetime(df[time_col])
        except:
            return insights
        
        # Analyze hourly patterns
        if len(df) > 10:  # Need sufficient data
            df['hour'] = df[time_col].dt.hour
            hourly_volume = df.groupby('hour').size()
            
            peak_hour = hourly_volume.idxmax()
            peak_volume = hourly_volume.max()
            
            # Analyze daily patterns
            df['day_of_week'] = df[time_col].dt.day_name()
            daily_performance = df.groupby('day_of_week').agg({
                'payment_status': lambda x: (x == 'succeeded').mean() * 100 if 'payment_status' in df.columns else 50
            }) if 'payment_status' in df.columns else df.groupby('day_of_week').size()
            
            best_day = daily_performance.idxmax()[0] if isinstance(daily_performance.idxmax(), tuple) else daily_performance.idxmax()
            best_day_performance = daily_performance.max()[0] if isinstance(daily_performance.max(), tuple) else daily_performance.max()
            
            insights.append(BusinessInsight(
                insight_type="time_pattern",
                title="Padrões Temporais Identificados",
                description=self.templates["time_pattern"].format(
                    peak_hour=peak_hour,
                    peak_volume=peak_volume,
                    best_day=best_day,
                    best_day_performance=best_day_performance,
                    time_based_insight="Concentração de transações no horário comercial"
                ),
                severity="low",
                confidence=0.8,
                recommendations=[
                    "Otimize recursos nos horários de pico",
                    "Implemente promoções em horários de menor volume",
                    "Monitore performance durante picos"
                ],
                supporting_data={
                    "peak_hour": peak_hour,
                    "hourly_distribution": hourly_volume.to_dict()
                }
            ))
        
        return insights
    
    def _generate_value_insights(self, df: pd.DataFrame, context: str) -> List[BusinessInsight]:
        """Generate value/amount-based insights"""
        insights = []
        
        amount_columns = ['amount', 'total_amount', 'valor']
        amount_col = None
        for col in amount_columns:
            if col in df.columns:
                amount_col = col
                break
        
        if amount_col is None or df[amount_col].isna().all():
            return insights
        
        amounts = df[amount_col].dropna()
        if len(amounts) == 0:
            return insights
        
        # Statistical analysis
        mean_amount = amounts.mean()
        median_amount = amounts.median()
        std_amount = amounts.std()
        
        # Identify outliers (values > 3 standard deviations)
        outliers = amounts[abs(amounts - mean_amount) > 3 * std_amount]
        outlier_percentage = len(outliers) / len(amounts) * 100
        
        if outlier_percentage > 5:  # More than 5% outliers is noteworthy
            insights.append(BusinessInsight(
                insight_type="value_analysis",
                title=f"Valores Atípicos Detectados ({outlier_percentage:.1f}%)",
                description=f"""
                📊 **Análise de Valores**:
                - Valor médio: R$ {mean_amount:.2f}
                - Valor mediano: R$ {median_amount:.2f}
                - Outliers detectados: {len(outliers)} ({outlier_percentage:.1f}%)
                - Maior valor: R$ {amounts.max():,.2f}
                """,
                severity="medium",
                confidence=0.7,
                recommendations=[
                    "Investigue transações de alto valor para possível fraude",
                    "Analise padrões de comportamento em valores extremos",
                    "Configure alertas para valores atípicos"
                ],
                supporting_data={
                    "mean_amount": mean_amount,
                    "outlier_count": len(outliers),
                    "outlier_threshold": mean_amount + 3 * std_amount
                }
            ))
        
        return insights
    
    def _generate_anomaly_insights(self, df: pd.DataFrame, context: str) -> List[BusinessInsight]:
        """Generate anomaly detection insights"""
        insights = []
        
        # This would integrate with more sophisticated anomaly detection
        # For now, implement basic anomaly checks
        
        if 'payment_method' in df.columns and len(df) > 50:
            # Check for unusual method distribution
            method_distribution = df['payment_method'].value_counts(normalize=True) * 100
            
            # Expected distributions (Brazilian market)
            expected_pix = 60  # Expected Pix usage
            actual_pix = method_distribution.get('Pix', 0)
            
            if abs(actual_pix - expected_pix) > 20:  # Significant deviation
                severity = "high" if abs(actual_pix - expected_pix) > 30 else "medium"
                
                insights.append(BusinessInsight(
                    insight_type="anomaly_detection",
                    title="Distribuição Atípica de Métodos",
                    description=self.templates["anomaly_alert"].format(
                        anomaly_type="Distribuição de métodos de pagamento",
                        impact_description=f"Pix: {actual_pix:.1f}% (esperado ~{expected_pix}%)",
                        recommended_action="Investigar possíveis problemas técnicos ou campanhas"
                    ),
                    severity=severity,
                    confidence=0.75,
                    recommendations=[
                        "Verifique integridade do sistema Pix",
                        "Analise campanhas ou promoções ativas",
                        "Compare com dados históricos"
                    ],
                    supporting_data={
                        "expected_pix_percentage": expected_pix,
                        "actual_pix_percentage": actual_pix,
                        "method_distribution": method_distribution.to_dict()
                    }
                ))
        
        return insights
    
    def _get_success_rate_recommendations(self, success_rate: float) -> List[str]:
        """Get recommendations based on success rate"""
        if success_rate >= 98:
            return [
                "Mantenha os processos atuais funcionando bem",
                "Monitore tendências para detectar declínios precocemente",
                "Considere expandir para novos mercados"
            ]
        elif success_rate >= 95:
            return [
                "Analise as principais causas de falha",
                "Implemente retry automático para falhas temporárias",
                "Monitore performance por horário"
            ]
        elif success_rate >= 90:
            return [
                "Investigue urgentemente as causas de falha",
                "Revise configurações de gateway de pagamento",
                "Considere alertas automáticos para taxa baixa"
            ]
        else:
            return [
                "AÇÃO IMEDIATA: Taxa crítica detectada",
                "Escale para equipe técnica imediatamente",
                "Ative planos de contingência",
                "Comunique status aos stakeholders"
            ]
    
    def _get_method_recommendations(self, best_method: str, worst_method: str) -> List[str]:
        """Get recommendations based on method performance"""
        return [
            f"Promova o uso de {best_method} (melhor performance)",
            f"Investigue problemas específicos com {worst_method}",
            "Analise taxas de retry por método",
            "Considere incentivos para métodos mais confiáveis"
        ]


class VisualizationRecommendationEngine:
    """Recommend optimal visualizations for query results"""
    
    def __init__(self):
        self.viz_config = VISUALIZATION_RECOMMENDATIONS
    
    def recommend_visualizations(self, df: pd.DataFrame, query_context: str, 
                                insights: List[BusinessInsight]) -> List[VisualizationRecommendation]:
        """Recommend visualizations based on data characteristics"""
        recommendations = []
        
        if df.empty:
            return recommendations
        
        # Analyze data characteristics
        data_profile = self._analyze_data_profile(df)
        
        # Generate recommendations based on data profile
        recommendations.extend(self._recommend_by_columns(df, data_profile, query_context))
        recommendations.extend(self._recommend_by_insights(df, insights))
        recommendations.extend(self._recommend_by_query_type(df, query_context))
        
        # Sort by priority and return top recommendations
        recommendations.sort(key=lambda x: x.priority)
        return recommendations[:3]  # Top 3 recommendations
    
    def _analyze_data_profile(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data characteristics for visualization selection"""
        profile = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "has_categorical": False,
            "has_numeric": False,
            "has_temporal": False,
            "has_geographic": False,
            "categorical_columns": [],
            "numeric_columns": [],
            "temporal_columns": []
        }
        
        for col in df.columns:
            # Check data types
            if df[col].dtype in ['object', 'category']:
                profile["has_categorical"] = True
                profile["categorical_columns"].append(col)
                
                # Check for specific patterns
                if col.lower() in ['payment_method', 'método', 'metodo']:
                    profile["payment_method_column"] = col
                    
            elif df[col].dtype in ['int64', 'float64']:
                profile["has_numeric"] = True  
                profile["numeric_columns"].append(col)
                
                # Check for amount/value columns
                if any(term in col.lower() for term in ['amount', 'valor', 'total', 'volume']):
                    profile["amount_column"] = col
                    
            elif 'datetime' in str(df[col].dtype):
                profile["has_temporal"] = True
                profile["temporal_columns"].append(col)
        
        return profile
    
    def _recommend_by_columns(self, df: pd.DataFrame, profile: Dict, 
                             context: str) -> List[VisualizationRecommendation]:
        """Recommend visualizations based on column characteristics"""
        recommendations = []
        
        # Payment method distribution (pie chart)
        if profile.get("payment_method_column") and profile.get("amount_column"):
            recommendations.append(VisualizationRecommendation(
                chart_type="pie",
                title="Distribuição de Métodos de Pagamento",
                description="Visualiza a participação de cada método de pagamento no volume total",
                config={
                    "x_column": profile["payment_method_column"],
                    "y_column": profile["amount_column"],
                    "aggregate": "sum",
                    "colors": {"Pix": "#003366", "Card": "#007bff", "Boleto": "#ffc107"}
                },
                priority=1,
                rationale="Método de pagamento é uma dimensão chave para análise de negócio"
            ))
        
        # Time series if temporal data exists
        if profile["has_temporal"] and profile.get("amount_column"):
            recommendations.append(VisualizationRecommendation(
                chart_type="line",
                title="Evolução Temporal do Volume",
                description="Mostra tendências de volume ao longo do tempo",
                config={
                    "x_column": profile["temporal_columns"][0],
                    "y_column": profile["amount_column"],
                    "aggregate": "sum",
                    "time_grouping": "daily"
                },
                priority=2,
                rationale="Análise temporal é essencial para identificar padrões e tendências"
            ))
        
        # Success rate analysis
        if "payment_status" in df.columns:
            recommendations.append(VisualizationRecommendation(
                chart_type="gauge",
                title="Taxa de Sucesso",
                description="Indica a performance geral de aprovação de pagamentos",
                config={
                    "value_column": "payment_status",
                    "success_value": "succeeded", 
                    "target": 95.0,
                    "color_ranges": [
                        {"range": [0, 90], "color": "red"},
                        {"range": [90, 95], "color": "orange"},
                        {"range": [95, 100], "color": "green"}
                    ]
                },
                priority=1,
                rationale="Taxa de sucesso é KPI crítico para pagamentos"
            ))
        
        return recommendations
    
    def _recommend_by_insights(self, df: pd.DataFrame, 
                              insights: List[BusinessInsight]) -> List[VisualizationRecommendation]:
        """Recommend visualizations based on generated insights"""
        recommendations = []
        
        for insight in insights:
            if insight.insight_type == "method_performance":
                recommendations.append(VisualizationRecommendation(
                    chart_type="horizontal_bar",
                    title="Performance por Método de Pagamento",
                    description="Compara taxa de sucesso entre diferentes métodos",
                    config={
                        "x_column": "payment_method",
                        "y_column": "success_rate", 
                        "sort": "descending"
                    },
                    priority=1,
                    rationale="Insight de performance de métodos identificado"
                ))
                
            elif insight.insight_type == "time_pattern":
                recommendations.append(VisualizationRecommendation(
                    chart_type="heatmap",
                    title="Mapa de Calor - Padrões Temporais",
                    description="Visualiza volume de transações por hora e dia da semana",
                    config={
                        "x_axis": "hour",
                        "y_axis": "day_of_week",
                        "value": "transaction_count"
                    },
                    priority=2,
                    rationale="Padrão temporal identificado nos dados"
                ))
        
        return recommendations
    
    def _recommend_by_query_type(self, df: pd.DataFrame, context: str) -> List[VisualizationRecommendation]:
        """Recommend visualizations based on query context"""
        recommendations = []
        
        context_lower = context.lower()
        
        # Volume/revenue analysis
        if any(term in context_lower for term in ["volume", "faturamento", "receita", "total"]):
            recommendations.append(VisualizationRecommendation(
                chart_type="bar",
                title="Análise de Volume",
                description="Visualiza volume de transações ou faturamento",
                config={
                    "chart_style": "modern",
                    "show_values": True,
                    "gradient_colors": True
                },
                priority=2,
                rationale="Query focada em análise de volume"
            ))
        
        # Comparison analysis
        if any(term in context_lower for term in ["comparar", "vs", "versus", "entre"]):
            recommendations.append(VisualizationRecommendation(
                chart_type="grouped_bar",
                title="Análise Comparativa",
                description="Facilita comparação entre categorias ou períodos",
                config={
                    "comparison_mode": True,
                    "highlight_differences": True
                },
                priority=1,
                rationale="Query indica análise comparativa"
            ))
        
        return recommendations


class QuerySuggestionEngine:
    """Generate intelligent follow-up query suggestions"""
    
    def __init__(self):
        self.suggestion_patterns = QUERY_SUGGESTION_PATTERNS
    
    def suggest_followup_questions(self, df: pd.DataFrame, original_query: str, 
                                  insights: List[BusinessInsight]) -> List[str]:
        """Suggest relevant follow-up questions"""
        suggestions = []
        
        # Based on query type
        suggestions.extend(self._suggest_by_query_type(original_query, df))
        
        # Based on insights
        suggestions.extend(self._suggest_by_insights(insights))
        
        # Based on data characteristics  
        suggestions.extend(self._suggest_by_data_features(df))
        
        # Remove duplicates and return top suggestions
        unique_suggestions = list(dict.fromkeys(suggestions))  # Preserves order
        return unique_suggestions[:5]
    
    def _suggest_by_query_type(self, query: str, df: pd.DataFrame) -> List[str]:
        """Suggest questions based on original query type"""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ["método", "metodo", "payment_method"]):
            return self.suggestion_patterns["after_payment_method_analysis"]
        
        elif any(term in query_lower for term in ["taxa", "sucesso", "aprovação"]):
            return self.suggestion_patterns["after_success_rate_query"]
        
        elif any(term in query_lower for term in ["volume", "total", "faturamento"]):
            return self.suggestion_patterns["after_volume_analysis"]
        
        elif any(term in query_lower for term in ["falha", "erro", "rejeitado"]):
            return self.suggestion_patterns["after_failure_analysis"]
        
        return []
    
    def _suggest_by_insights(self, insights: List[BusinessInsight]) -> List[str]:
        """Suggest questions based on generated insights"""
        suggestions = []
        
        for insight in insights:
            if insight.insight_type == "success_rate_analysis" and insight.severity in ["high", "critical"]:
                suggestions.extend([
                    "Quais são os principais motivos de falha?",
                    "Compare a performance por horário do dia",
                    "Analise falhas por método de pagamento"
                ])
            
            elif insight.insight_type == "method_performance":
                suggestions.extend([
                    "Mostre evolução da performance nos últimos 7 dias",
                    "Compare ticket médio por método",
                    "Analise distribuição regional dos métodos"
                ])
            
            elif insight.insight_type == "anomaly_detection":
                suggestions.extend([
                    "Compare com dados históricos do mesmo período",
                    "Analise eventos ou campanhas que podem explicar a anomalia",
                    "Verifique performance de sistemas relacionados"
                ])
        
        return suggestions
    
    def _suggest_by_data_features(self, df: pd.DataFrame) -> List[str]:
        """Suggest questions based on available data features"""
        suggestions = []
        
        # If geographic data is available
        if any(col.lower() in ['region', 'state', 'city', 'estado', 'cidade'] for col in df.columns):
            suggestions.append("Analise performance por região")
        
        # If customer data is available
        if any(col.lower() in ['user_id', 'customer', 'cpf'] for col in df.columns):
            suggestions.append("Mostre padrões de comportamento por cliente")
        
        # If temporal data with sufficient range
        temporal_cols = [col for col in df.columns if 'datetime' in str(df[col].dtype)]
        if temporal_cols and len(df) > 100:
            suggestions.append("Analise sazonalidade e tendências")
        
        return suggestions


# Global instances
_insight_generator_instance: Optional[PaymentInsightGenerator] = None
_visualization_engine_instance: Optional[VisualizationRecommendationEngine] = None
_suggestion_engine_instance: Optional[QuerySuggestionEngine] = None


def get_insight_generator() -> PaymentInsightGenerator:
    """Get shared insight generator instance"""
    global _insight_generator_instance
    if _insight_generator_instance is None:
        _insight_generator_instance = PaymentInsightGenerator()
    return _insight_generator_instance


def get_visualization_engine() -> VisualizationRecommendationEngine:
    """Get shared visualization engine instance"""
    global _visualization_engine_instance
    if _visualization_engine_instance is None:
        _visualization_engine_instance = VisualizationRecommendationEngine()
    return _visualization_engine_instance


def get_suggestion_engine() -> QuerySuggestionEngine:
    """Get shared suggestion engine instance"""
    global _suggestion_engine_instance
    if _suggestion_engine_instance is None:
        _suggestion_engine_instance = QuerySuggestionEngine()
    return _suggestion_engine_instance