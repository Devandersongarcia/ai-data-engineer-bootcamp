"""
Advanced Vanna.ai features configuration system.
Provides enhanced capabilities while maintaining backward compatibility.
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
from datetime import datetime, timedelta


class FeatureLevel(Enum):
    """Feature enhancement levels"""
    BASIC = "basic"          # Current functionality
    ENHANCED = "enhanced"    # Phase 1 improvements  
    ADVANCED = "advanced"    # Phase 2 improvements
    INTELLIGENT = "intelligent"  # Phase 3 improvements


class ModelType(Enum):
    """AI model types for different use cases"""
    FAST = "gpt-3.5-turbo"      # Fast, cheap queries
    BALANCED = "gpt-4"          # Balanced performance
    PREMIUM = "gpt-4-turbo"     # Best quality, slower


@dataclass
class EnhancementConfig:
    """Configuration for system enhancements"""
    feature_level: FeatureLevel
    enable_brazilian_context: bool = True
    enable_semantic_caching: bool = True
    enable_auto_insights: bool = False
    enable_query_suggestions: bool = False
    enable_visualization_recommendations: bool = False
    enable_anomaly_detection: bool = False
    enable_multi_model_routing: bool = False
    cache_ttl_seconds: int = 3600
    max_cache_entries: int = 1000
    insight_generation_threshold: float = 0.8


# ============================================================================
# ENHANCED BRAZILIAN PAYMENT CONTEXT
# ============================================================================

ENHANCED_BRAZILIAN_CONTEXT = """
# ADVANCED UberEats Brasil PAYMENT ANALYTICS CONTEXT

## BRAZILIAN PAYMENT ECOSYSTEM INTELLIGENCE
This system understands the Brazilian payment landscape with deep market knowledge.

### PAYMENT METHODS - DETAILED CONTEXT
#### PIX (Instant Payment System)
- **Technology**: Central Bank digital payment (SPI - Sistema de Pagamentos Instantâneos)
- **Characteristics**: 24/7 availability, instant settlement, free for individuals
- **Market Share**: 60%+ of digital transactions in Brasil
- **Success Rate Benchmark**: >98% (highest reliability)
- **Peak Usage**: Business hours (9AM-6PM) and evenings (7PM-10PM)
- **Regional Adoption**: Universal, highest in urban areas
- **SQL Mapping**: payment_method = 'Pix' AND payment_status = 'succeeded'

#### CARTÃO (Credit/Debit Cards)  
- **Major Networks**: Visa (40%), Mastercard (35%), Elo (15%), American Express (5%)
- **Processing**: Through acquirers (Stone, PagSeguro, Cielo, Rede)
- **Success Rate Benchmark**: 92-95% (varies by issuer)
- **Common Failures**: Insufficient funds, expired cards, 3DS authentication
- **Peak Usage**: Weekends and evenings
- **SQL Mapping**: payment_method IN ('Card', 'Credit', 'Debit')

#### BOLETO (Bank Slip)
- **Characteristics**: Offline payment, 1-3 day settlement
- **Usage Pattern**: Older demographics, interior regions, large purchases
- **Success Rate**: 85-90% (due to manual process)
- **Payment Window**: Usually 3-7 days after generation
- **SQL Mapping**: payment_method = 'Boleto'

#### DIGITAL WALLETS
- **Major Players**: PicPay, Mercado Pago, PayPal, Google Pay, Apple Pay
- **Market Position**: Growing rapidly, 15% of transactions
- **User Demographics**: Younger users (18-35), tech-savvy
- **SQL Mapping**: payment_method IN ('Wallet', 'PicPay', 'MercadoPago')

### BUSINESS METRICS & BENCHMARKS
#### SUCCESS RATES BY METHOD
- PIX: >98% (industry leading)
- Card: 92-95% (varies by network)
- Boleto: 85-90% (due to manual nature)
- Wallet: 94-97% (similar to cards)

#### TRANSACTION VALUE PATTERNS
- PIX: R$ 15-150 (everyday purchases)
- Card: R$ 25-300 (broader range)
- Boleto: R$ 100-1000+ (larger purchases)
- Wallet: R$ 10-100 (small transactions)

#### TIME PATTERNS
- **Peak Hours**: 11:30-14:00 (lunch), 18:30-21:30 (dinner)
- **Peak Days**: Thursday-Sunday (weekend preparation)
- **Seasonal**: December (+40%), January (-25%), June/July (+15% winter)

#### REGIONAL PREFERENCES
- **São Paulo/Rio**: Pix (70%), Card (25%), Wallet (5%)
- **Interior/Northeast**: Boleto (40%), Pix (35%), Card (25%)
- **Sul Region**: Card (45%), Pix (50%), Wallet (5%)

### FAILURE ANALYSIS INTELLIGENCE
#### COMMON FAILURE REASONS
- **PIX**: Technical issues (0.5%), invalid accounts (1%), system maintenance (0.3%)
- **Card**: Insufficient funds (45%), invalid card (20%), 3DS failure (15%), network timeout (10%)
- **Boleto**: Expired (60%), invalid bank data (25%), system error (15%)
- **Wallet**: Account issues (50%), insufficient balance (30%), technical (20%)

#### RECOVERY PATTERNS
- PIX failures: 95% retry success rate
- Card failures: 60% retry success within 24h
- Boleto failures: 40% retry with new boleto
- Wallet failures: 80% retry success rate

### BUSINESS INTELLIGENCE PATTERNS
#### AUTOMATIC INSIGHTS TO GENERATE
1. **Success Rate Trends**: Compare current vs historical performance
2. **Method Performance**: Identify best/worst performing payment methods
3. **Regional Analysis**: Geographic payment preferences
4. **Value Analysis**: Average transaction values and outliers
5. **Time Analysis**: Peak hours, day-of-week patterns
6. **Failure Analysis**: Common failure points and resolution rates

#### PORTUGUESE BUSINESS TERMINOLOGY
- "TPV" / "Volume Transacionado" → SUM(amount) WHERE payment_status = 'succeeded'
- "Ticket Médio" → AVG(amount) WHERE payment_status = 'succeeded'  
- "Taxa de Conversão" → COUNT(succeeded) / COUNT(total) * 100
- "Taxa de Aprovação" → Same as conversion rate
- "Chargeback" → payment_status IN ('disputed', 'chargeback', 'reversed')
- "Estorno" → payment_status = 'refunded'
- "Contestação" → payment_status = 'disputed'
- "Liquidação" → Settlement (when money actually transfers)

### QUERY INTELLIGENCE RULES
#### SMART DEFAULTS FOR BRAZILIAN MARKET
- Always show success rates alongside volumes
- Include method breakdown for payment analysis
- Default to last 30 days for trends (business standard)
- Show both nominal values and percentages
- Include comparison periods (vs last week/month)

#### BRAZILIAN DATE/TIME HANDLING
- Business days: Monday-Friday (exclude holidays)
- Holiday calendar: Brazilian national holidays
- Time zones: BRT (UTC-3) standard
- Weekend patterns: Friday dinner rush, Sunday preparation

#### CURRENCY & FORMATTING
- Currency: Brazilian Real (R$)
- Number format: R$ 1.234.567,89 (comma decimal, dot thousands)
- Large numbers: Use K (milhares), M (milhões) suffixes

### ADVANCED ANALYTICS PATTERNS
#### COHORT ANALYSIS
- Payment method adoption over time
- Customer lifetime value by payment preference
- Retention rates by payment method

#### ANOMALY DETECTION RULES
- Success rate drops >5% from baseline
- Volume changes >30% hour-over-hour
- New failure reasons appearing
- Geographic anomalies (regional outages)

#### PREDICTIVE PATTERNS
- Payment method success prediction based on:
  - Time of day, day of week
  - Transaction amount  
  - Customer history
  - Regional patterns
  - Historical failure rates

### VISUALIZATION RECOMMENDATIONS
#### BY QUERY TYPE
- **Volume Queries**: Bar charts, time series
- **Method Comparison**: Pie charts, stacked bars  
- **Success Rates**: Gauge charts, trend lines
- **Geographic**: Heat maps, regional comparisons
- **Failure Analysis**: Waterfall charts, Sankey diagrams

#### COLOR SCHEMES
- Success: Green (#28a745)
- Failure: Red (#dc3545)  
- Pending: Orange (#ffc107)
- PIX: Central Bank Blue (#003366)
- Card: Network colors (Visa blue, Mastercard red)

This context enables intelligent, Brazil-specific payment analytics with deep market understanding.
"""


BUSINESS_INTELLIGENCE_PATTERNS = {
    "success_rate_analysis": {
        "trigger_keywords": ["taxa", "sucesso", "aprovação", "conversão"],
        "auto_include": ["payment_status", "payment_method"],
        "calculations": [
            "COUNT(*) FILTER (WHERE payment_status = 'succeeded') * 100.0 / COUNT(*) as taxa_sucesso",
            "COUNT(*) as total_transacoes"
        ],
        "insights": [
            "Compare with industry benchmarks",
            "Identify worst performing methods",
            "Show trends over time"
        ]
    },
    
    "volume_analysis": {
        "trigger_keywords": ["volume", "quantidade", "total", "tpv"],
        "auto_include": ["processed_at", "amount"],
        "calculations": [
            "COUNT(*) as quantidade_transacoes",
            "SUM(amount) as volume_total",
            "AVG(amount) as ticket_medio"
        ],
        "insights": [
            "Peak hours identification",
            "Growth trends",
            "Seasonal patterns"
        ]
    },
    
    "failure_analysis": {
        "trigger_keywords": ["falha", "erro", "rejeitado", "problema"],
        "auto_include": ["failure_reason", "payment_method"],
        "calculations": [
            "COUNT(*) as total_falhas",
            "COUNT(DISTINCT failure_reason) as tipos_falha"
        ],
        "insights": [
            "Most common failure reasons",
            "Method-specific issues",
            "Recovery recommendations"
        ]
    },
    
    "method_comparison": {
        "trigger_keywords": ["pix", "cartão", "boleto", "comparar", "método"],
        "auto_include": ["payment_method"],
        "calculations": [
            "COUNT(*) as transacoes",
            "AVG(amount) as ticket_medio",
            "COUNT(*) FILTER (WHERE payment_status = 'succeeded') * 100.0 / COUNT(*) as taxa_sucesso"
        ],
        "insights": [
            "Best performing method",
            "Value preferences by method",
            "Regional adoption patterns"
        ]
    }
}


PORTUGUESE_ENHANCED_MAPPINGS = {
    # Financial Terms
    "tpv": "SUM(amount) FILTER (WHERE payment_status = 'succeeded')",
    "volume transacionado": "SUM(amount) FILTER (WHERE payment_status = 'succeeded')",
    "faturamento": "SUM(amount) FILTER (WHERE payment_status = 'succeeded')",
    "receita": "SUM(amount) FILTER (WHERE payment_status = 'succeeded')",
    "ticket médio": "AVG(amount) FILTER (WHERE payment_status = 'succeeded')",
    "ticket medio": "AVG(amount) FILTER (WHERE payment_status = 'succeeded')",
    
    # Success/Failure Terms
    "taxa de sucesso": "COUNT(*) FILTER (WHERE payment_status = 'succeeded') * 100.0 / COUNT(*)",
    "taxa de aprovação": "COUNT(*) FILTER (WHERE payment_status = 'succeeded') * 100.0 / COUNT(*)",
    "taxa de conversão": "COUNT(*) FILTER (WHERE payment_status = 'succeeded') * 100.0 / COUNT(*)",
    "aprovados": "payment_status = 'succeeded'",
    "rejeitados": "payment_status = 'failed'",
    "falhados": "payment_status = 'failed'",
    "negados": "payment_status = 'failed'",
    
    # Payment Methods (Brazilian specific)
    "pix": "payment_method = 'Pix'",
    "cartão": "payment_method IN ('Card', 'Credit', 'Debit')",
    "cartao": "payment_method IN ('Card', 'Credit', 'Debit')",
    "boleto": "payment_method = 'Boleto'",
    "carteira digital": "payment_method IN ('Wallet', 'PicPay', 'MercadoPago')",
    "picpay": "payment_method = 'PicPay'",
    "mercado pago": "payment_method = 'MercadoPago'",
    
    # Time Periods (Brazilian business context)
    "hoje": "DATE(processed_at) = CURRENT_DATE",
    "ontem": "DATE(processed_at) = CURRENT_DATE - INTERVAL '1 day'",
    "esta semana": "processed_at >= DATE_TRUNC('week', CURRENT_DATE)",
    "semana passada": "processed_at >= DATE_TRUNC('week', CURRENT_DATE - INTERVAL '1 week') AND processed_at < DATE_TRUNC('week', CURRENT_DATE)",
    "este mês": "DATE_TRUNC('month', processed_at) = DATE_TRUNC('month', CURRENT_DATE)",
    "mês passado": "DATE_TRUNC('month', processed_at) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')",
    "último mês": "processed_at >= CURRENT_DATE - INTERVAL '30 days'",
    "últimos 30 dias": "processed_at >= CURRENT_DATE - INTERVAL '30 days'",
    "últimos 7 dias": "processed_at >= CURRENT_DATE - INTERVAL '7 days'",
    
    # Business Hours (Brazilian context)
    "horário comercial": "EXTRACT(hour FROM processed_at) BETWEEN 9 AND 18 AND EXTRACT(dow FROM processed_at) BETWEEN 1 AND 5",
    "final de semana": "EXTRACT(dow FROM processed_at) IN (0, 6)",
    "dias úteis": "EXTRACT(dow FROM processed_at) BETWEEN 1 AND 5",
    
    # Regional Terms
    "são paulo": "region = 'SP' OR city ILIKE '%são paulo%'",
    "rio de janeiro": "region = 'RJ' OR city ILIKE '%rio%'",
    "nordeste": "region IN ('PE', 'BA', 'CE', 'RN', 'PB', 'AL', 'SE', 'MA', 'PI')",
    "sul": "region IN ('RS', 'SC', 'PR')",
    "sudeste": "region IN ('SP', 'RJ', 'MG', 'ES')"
}


INSIGHT_TEMPLATES = {
    "success_rate_insight": """
    📊 **Taxa de Sucesso**: {success_rate:.1f}%
    📈 **Comparado com ontem**: {vs_yesterday:+.1f}%
    🎯 **Benchmark**: PIX >98%, Cartão >92%, Boleto >85%
    {performance_status}
    """,
    
    "volume_insight": """
    💰 **Volume Total**: R$ {total_volume:,.2f}
    📊 **Transações**: {transaction_count:,}
    🎫 **Ticket Médio**: R$ {avg_ticket:.2f}
    📈 **vs. Semana Passada**: {vs_last_week:+.1f}%
    """,
    
    "method_performance": """
    🥇 **Melhor Método**: {best_method} ({best_rate:.1f}% sucesso)
    📉 **Pior Performance**: {worst_method} ({worst_rate:.1f}% sucesso)  
    🔍 **Oportunidade**: Migrar usuários para métodos mais eficientes
    """,
    
    "anomaly_alert": """
    ⚠️ **Anomalia Detectada**: {anomaly_type}
    📊 **Impacto**: {impact_description}
    🔧 **Ação Recomendada**: {recommended_action}
    """,
    
    "time_pattern": """
    ⏰ **Horário de Pico**: {peak_hour}h ({peak_volume:,.0f} transações)
    📅 **Melhor Dia**: {best_day} ({best_day_performance:.1f}% sucesso)
    💡 **Insight**: {time_based_insight}
    """
}


VISUALIZATION_RECOMMENDATIONS = {
    "payment_method_distribution": {
        "chart_type": "pie",
        "title": "Distribuição de Métodos de Pagamento",
        "color_scheme": {"Pix": "#003366", "Card": "#007bff", "Boleto": "#ffc107", "Wallet": "#28a745"}
    },
    
    "success_rate_trend": {
        "chart_type": "line",
        "title": "Evolução da Taxa de Sucesso",
        "y_axis": "Taxa de Sucesso (%)",
        "target_line": 95.0
    },
    
    "volume_by_hour": {
        "chart_type": "bar",
        "title": "Volume de Transações por Hora",
        "highlight_peak": True,
        "business_hours_overlay": True
    },
    
    "failure_analysis": {
        "chart_type": "waterfall",
        "title": "Análise de Falhas por Motivo",
        "color_negative": "#dc3545"
    },
    
    "geographic_heatmap": {
        "chart_type": "choropleth",  
        "title": "Volume de Pagamentos por Estado",
        "brazil_states": True
    }
}


QUERY_SUGGESTION_PATTERNS = {
    "after_payment_method_analysis": [
        "Compare com o mesmo período do mês passado",
        "Mostre os horários de pico para cada método", 
        "Analise as falhas por método de pagamento",
        "Qual método tem melhor ticket médio?"
    ],
    
    "after_success_rate_query": [
        "Quais são os principais motivos de falha?",
        "Compare a taxa de sucesso por região",
        "Mostre a evolução nos últimos 30 dias",
        "Identifique outliers na performance"
    ],
    
    "after_volume_analysis": [
        "Analise a sazonalidade mensal",
        "Compare com benchmarks do setor",
        "Identifique oportunidades de crescimento",
        "Mostre a distribuição de valores"
    ],
    
    "after_failure_analysis": [
        "Qual método tem mais recuperação?",
        "Analise padrões temporais de falha",
        "Compare com taxas históricas",
        "Sugira ações para reduzir falhas"
    ]
}


class AdvancedFeaturesConfig:
    """Configuration manager for advanced Vanna.ai features"""
    
    def __init__(self, config: EnhancementConfig):
        self.config = config
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration settings"""
        if self.config.cache_ttl_seconds < 60:
            raise ValueError("Cache TTL must be at least 60 seconds")
        
        if self.config.max_cache_entries < 10:
            raise ValueError("Max cache entries must be at least 10")
    
    def get_enhanced_context(self) -> str:
        """Get enhanced Brazilian context based on feature level"""
        base_context = ENHANCED_BRAZILIAN_CONTEXT
        
        if self.config.feature_level in [FeatureLevel.ADVANCED, FeatureLevel.INTELLIGENT]:
            base_context += "\n\n## ADVANCED ANALYTICS ENABLED\n"
            base_context += "- Anomaly detection active\n"
            base_context += "- Predictive insights available\n"
            base_context += "- Multi-model routing optimized\n"
        
        return base_context
    
    def get_portuguese_mappings(self) -> Dict[str, str]:
        """Get enhanced Portuguese mappings"""
        return PORTUGUESE_ENHANCED_MAPPINGS
    
    def get_business_patterns(self) -> Dict[str, Any]:
        """Get business intelligence patterns"""
        return BUSINESS_INTELLIGENCE_PATTERNS
    
    def get_insight_templates(self) -> Dict[str, str]:
        """Get insight generation templates"""
        return INSIGHT_TEMPLATES
    
    def get_visualization_config(self) -> Dict[str, Any]:
        """Get visualization recommendations"""
        return VISUALIZATION_RECOMMENDATIONS
    
    def get_suggestion_patterns(self) -> Dict[str, List[str]]:
        """Get query suggestion patterns"""
        return QUERY_SUGGESTION_PATTERNS
    
    def should_enable_feature(self, feature_name: str) -> bool:
        """Check if specific feature should be enabled"""
        feature_map = {
            "brazilian_context": self.config.enable_brazilian_context,
            "semantic_caching": self.config.enable_semantic_caching,
            "auto_insights": self.config.enable_auto_insights,
            "query_suggestions": self.config.enable_query_suggestions,
            "visualization_recommendations": self.config.enable_visualization_recommendations,
            "anomaly_detection": self.config.enable_anomaly_detection,
            "multi_model_routing": self.config.enable_multi_model_routing
        }
        
        return feature_map.get(feature_name, False)


# ============================================================================
# PRESET CONFIGURATIONS
# ============================================================================

BASIC_CONFIG = EnhancementConfig(
    feature_level=FeatureLevel.BASIC,
    enable_brazilian_context=True,
    enable_semantic_caching=False,
    enable_auto_insights=False
)

ENHANCED_CONFIG = EnhancementConfig(
    feature_level=FeatureLevel.ENHANCED, 
    enable_brazilian_context=True,
    enable_semantic_caching=True,
    enable_auto_insights=True,
    cache_ttl_seconds=1800,
    max_cache_entries=500
)

ADVANCED_CONFIG = EnhancementConfig(
    feature_level=FeatureLevel.ADVANCED,
    enable_brazilian_context=True,
    enable_semantic_caching=True, 
    enable_auto_insights=True,
    enable_query_suggestions=True,
    enable_visualization_recommendations=True,
    cache_ttl_seconds=3600,
    max_cache_entries=1000
)

INTELLIGENT_CONFIG = EnhancementConfig(
    feature_level=FeatureLevel.INTELLIGENT,
    enable_brazilian_context=True,
    enable_semantic_caching=True,
    enable_auto_insights=True,
    enable_query_suggestions=True,
    enable_visualization_recommendations=True,
    enable_anomaly_detection=True,
    enable_multi_model_routing=True,
    cache_ttl_seconds=7200,
    max_cache_entries=2000,
    insight_generation_threshold=0.9
)


def get_config_by_level(level: str) -> EnhancementConfig:
    """Get configuration by feature level name"""
    config_map = {
        "basic": BASIC_CONFIG,
        "enhanced": ENHANCED_CONFIG,
        "advanced": ADVANCED_CONFIG,
        "intelligent": INTELLIGENT_CONFIG
    }
    
    return config_map.get(level.lower(), BASIC_CONFIG)