"""
Advanced Analytics Package for Fraud Detection
Real-time analytics and insights from Spark streaming data
"""

from .streamlit_dashboard import StreamlitAnalyticsDashboard
from .data_models import AnalyticsDataModel, FraudMetrics, StreamingMetrics
from .real_time_processor import RealTimeAnalyticsProcessor

__all__ = [
    "StreamlitAnalyticsDashboard",
    "AnalyticsDataModel", 
    "FraudMetrics",
    "StreamingMetrics",
    "RealTimeAnalyticsProcessor"
]