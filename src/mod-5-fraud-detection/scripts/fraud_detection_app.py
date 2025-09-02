"""
🔍 UberEats Fraud Detection Dashboard & AI Chat
Professional Streamlit application for fraud detection analytics and MindsDB agent interaction
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import json
import logging
import time
from typing import Dict, List, Any, Optional

# Configure comprehensive logging
try:
    from mindsdb_interface.logging_config import (
        setup_logging, log_function_call, log_performance_metric, log_system_info
    )
    
    # Initialize logging
    setup_logging(level="INFO", console_output=True)
    logger = logging.getLogger(__name__)
    
    # Log system information on startup
    if 'app_started' not in st.session_state:
        log_system_info()
        logger.info("🚀 Starting UberEats Fraud Detection Dashboard")
        st.session_state.app_started = True
        
except ImportError:
    # Fallback to basic logging if logging_config is not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# Import our custom modules
try:
    from mindsdb_interface.mindsdb_client import FraudDetectionMindsDBClient
    from mindsdb_interface.fraud_data_service import FraudDataService
    logger.info("✅ Successfully imported MindsDB interface modules")
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    st.error(f"❌ Import error: {e}")
    st.info("💡 Make sure the mindsdb_interface module is properly installed")

# Page configuration
st.set_page_config(
    page_title="🔍 UberEats Fraud Detection",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main theme colors */
    .main-header {
        background: linear-gradient(90deg, #FF6B6B 0%, #4ECDC4 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #FF6B6B;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    .alert-high {
        background-color: #ffebee;
        border: 1px solid #f44336;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .alert-medium {
        background-color: #fff3e0;
        border: 1px solid #ff9800;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .alert-low {
        background-color: #e8f5e8;
        border: 1px solid #4caf50;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        background-color: #f8f9fa;
        border-left: 4px solid #4ECDC4;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f0f2f6;
        border-radius: 8px 8px 0 0;
        padding-left: 20px;
        padding-right: 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #FF6B6B;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'mindsdb_client' not in st.session_state:
    st.session_state.mindsdb_client = None
    st.session_state.connected = False
    st.session_state.chat_history = []

if 'data_service' not in st.session_state:
    st.session_state.data_service = None

# Header
st.markdown("""
<div class="main-header">
    <h1>🔍 UberEats Fraud Detection Center</h1>
    <p>Real-time fraud monitoring, AI-powered analytics & intelligent agent assistance</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for connection settings
st.sidebar.markdown("## 🔧 Configuration")

# MindsDB Connection
st.sidebar.markdown("### 🧠 MindsDB Agent")
mindsdb_url = st.sidebar.text_input(
    "MindsDB Server URL", 
    value="http://127.0.0.1:47334",
    help="MindsDB server URL"
)

agent_name = st.sidebar.text_input(
    "Agent Name", 
    value="agent_fraud_analytics",
    help="Name of the fraud analytics agent"
)

if st.sidebar.button("🔗 Connect to Agent", type="primary"):
    with st.sidebar:
        with st.spinner("Connecting to MindsDB agent..."):
            client = FraudDetectionMindsDBClient(mindsdb_url)
            if client.connect_to_agent(agent_name):
                st.session_state.mindsdb_client = client
                st.session_state.connected = True
                st.success("✅ Connected to fraud analytics agent!")
            else:
                st.error("❌ Failed to connect to agent")
                st.info("💡 Make sure MindsDB is running and the agent exists")

# Database Connection
st.sidebar.markdown("### 🗄️ Database")
db_host = st.sidebar.text_input("Database Host", value="localhost")
db_port = st.sidebar.number_input("Database Port", value=5432)
db_name = st.sidebar.text_input("Database Name", value="uberats_fraud")
db_user = st.sidebar.text_input("Database User", value="postgres")
db_password = st.sidebar.text_input("Database Password", value="postgres", type="password")

if st.sidebar.button("🔗 Connect to Database"):
    with st.sidebar:
        with st.spinner("Connecting to database..."):
            try:
                service = FraudDataService(
                    host=db_host,
                    port=db_port,
                    database=db_name,
                    user=db_user,
                    password=db_password
                )
                if service.connect():
                    st.session_state.data_service = service
                    st.success("✅ Connected to fraud database!")
                else:
                    st.error("❌ Failed to connect to database")
            except Exception as e:
                st.error(f"❌ Database connection error: {e}")

# Connection status
st.sidebar.markdown("### 📊 Status")
if st.session_state.connected:
    st.sidebar.success("🟢 MindsDB Agent: Connected")
else:
    st.sidebar.error("🔴 MindsDB Agent: Disconnected")

if st.session_state.data_service:
    st.sidebar.success("🟢 Database: Connected")
else:
    st.sidebar.error("🔴 Database: Disconnected")

# Main content tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard", 
    "🚨 Real-time Alerts", 
    "💬 AI Chat Assistant", 
    "🔍 Order Search"
])

# Tab 1: Dashboard
with tab1:
    st.markdown("## 📊 Fraud Detection Dashboard")
    
    if st.session_state.data_service:
        try:
            # Get summary statistics
            with st.spinner("Loading fraud detection metrics..."):
                summary_stats = st.session_state.data_service.get_fraud_summary_stats()
            
            if summary_stats:
                # Display key metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Total Orders (24h)",
                        f"{summary_stats.get('total_orders', 0):,}",
                        help="Total orders processed in last 24 hours"
                    )
                
                with col2:
                    high_risk = summary_stats.get('high_risk_orders', 0)
                    total = summary_stats.get('total_orders', 1)
                    fraud_rate = (high_risk / total) * 100 if total > 0 else 0
                    st.metric(
                        "High Risk Orders",
                        f"{high_risk:,}",
                        f"{fraud_rate:.1f}% fraud rate"
                    )
                
                with col3:
                    st.metric(
                        "Agent Analysis Required",
                        f"{summary_stats.get('agent_analysis_required', 0):,}",
                        help="Orders requiring AI agent analysis"
                    )
                
                with col4:
                    avg_score = summary_stats.get('avg_fraud_score', 0)
                    st.metric(
                        "Avg Fraud Score",
                        f"{avg_score:.3f}",
                        help="Average fraud risk score"
                    )
            
            # Fraud trends chart
            st.markdown("### 📈 Fraud Detection Trends (24 hours)")
            with st.spinner("Loading trend data..."):
                trend_data = st.session_state.data_service.get_fraud_trends_hourly(24)
            
            if trend_data is not None and len(trend_data) > 0:
                # Create trend visualization
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=("Order Volume by Risk Level", "Average Fraud Score"),
                    vertical_spacing=0.12
                )
                
                # Stacked bar chart for risk levels
                fig.add_trace(
                    go.Bar(
                        x=trend_data['hour'],
                        y=trend_data['high_risk_count'],
                        name='High Risk',
                        marker_color='#FF6B6B'
                    ),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Bar(
                        x=trend_data['hour'],
                        y=trend_data['medium_risk_count'],
                        name='Medium Risk',
                        marker_color='#FFB347'
                    ),
                    row=1, col=1
                )
                
                # Line chart for average fraud score
                fig.add_trace(
                    go.Scatter(
                        x=trend_data['hour'],
                        y=trend_data['avg_fraud_score'],
                        mode='lines+markers',
                        name='Avg Fraud Score',
                        line=dict(color='#4ECDC4', width=3),
                        marker=dict(size=6)
                    ),
                    row=2, col=1
                )
                
                fig.update_layout(
                    height=500,
                    title="Fraud Detection Trends",
                    barmode='stack'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Fraud patterns analysis
            st.markdown("### 🔍 Most Common Fraud Patterns")
            with st.spinner("Analyzing fraud patterns..."):
                pattern_data = st.session_state.data_service.get_fraud_patterns_frequency()
            
            if pattern_data is not None and len(pattern_data) > 0:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    fig = px.bar(
                        pattern_data.head(10),
                        x='frequency',
                        y='pattern_reason',
                        orientation='h',
                        color='avg_score',
                        color_continuous_scale='Reds',
                        title="Top Fraud Patterns (Last 7 Days)"
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("**Pattern Analysis**")
                    for _, pattern in pattern_data.head(5).iterrows():
                        st.markdown(f"""
                        <div class="metric-card">
                            <strong>{pattern['pattern_reason']}</strong><br>
                            Frequency: {pattern['frequency']}<br>
                            Avg Score: {pattern['avg_score']:.3f}
                        </div>
                        """, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"❌ Error loading dashboard data: {e}")
            st.info("💡 Make sure the database connection is working and contains fraud data")
    else:
        st.info("🔌 Connect to the database to view fraud detection metrics")

# Tab 2: Real-time Alerts
with tab2:
    st.markdown("## 🚨 Real-time Fraud Alerts")
    
    if st.session_state.data_service:
        try:
            # Refresh button
            if st.button("🔄 Refresh Alerts", type="primary"):
                st.rerun()
            
            # Get high-risk orders
            with st.spinner("Loading high-risk alerts..."):
                high_risk_orders = st.session_state.data_service.get_recent_high_risk_orders(20)
            
            if high_risk_orders is not None and len(high_risk_orders) > 0:
                st.markdown(f"### ⚠️ {len(high_risk_orders)} High-Risk Orders Detected")
                
                # Filter options
                col1, col2, col3 = st.columns(3)
                with col1:
                    risk_filter = st.selectbox(
                        "Filter by Risk Level",
                        ["All", "HIGH_RISK", "MEDIUM_RISK"]
                    )
                
                with col2:
                    show_analyzed = st.checkbox("Show Agent-Analyzed Only", False)
                
                with col3:
                    sort_by = st.selectbox(
                        "Sort by",
                        ["Fraud Score", "Date", "Amount"]
                    )
                
                # Apply filters
                filtered_orders = high_risk_orders.copy()
                if risk_filter != "All":
                    filtered_orders = filtered_orders[
                        filtered_orders['fraud_prediction'] == risk_filter
                    ]
                
                if show_analyzed:
                    filtered_orders = filtered_orders[
                        filtered_orders['agent_fraud_score'].notna()
                    ]
                
                # Display alerts
                for _, order in filtered_orders.iterrows():
                    risk_level = order['fraud_prediction']
                    css_class = {
                        'HIGH_RISK': 'alert-high',
                        'MEDIUM_RISK': 'alert-medium',
                        'LEGITIMATE': 'alert-low'
                    }.get(risk_level, 'alert-medium')
                    
                    # Format fraud reasons
                    fraud_reasons = order['fraud_reasons']
                    if isinstance(fraud_reasons, str):
                        try:
                            fraud_reasons = json.loads(fraud_reasons.replace("'", '"'))
                        except:
                            fraud_reasons = [fraud_reasons]
                    elif fraud_reasons is None:
                        fraud_reasons = ["No specific reasons"]
                    
                    reasons_text = ", ".join(fraud_reasons) if fraud_reasons else "No reasons"
                    
                    # Agent analysis status
                    agent_status = "🤖 Analyzed" if pd.notna(order['agent_fraud_score']) else "⏳ Pending"
                    agent_score = f" (Agent Score: {order['agent_fraud_score']:.3f})" if pd.notna(order['agent_fraud_score']) else ""
                    
                    st.markdown(f"""
                    <div class="{css_class}">
                        <h4>🚨 Order: {order['order_id']}</h4>
                        <p><strong>User:</strong> {order['user_id']} | 
                           <strong>Amount:</strong> ${order['total_amount']:.2f} | 
                           <strong>Risk Score:</strong> {order['spark_fraud_score']:.3f}</p>
                        <p><strong>Risk Level:</strong> {risk_level} | 
                           <strong>Priority:</strong> {order['priority_level']}</p>
                        <p><strong>Fraud Indicators:</strong> {reasons_text}</p>
                        <p><strong>Agent Status:</strong> {agent_status}{agent_score}</p>
                        <p><strong>Detected:</strong> {order['created_at']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("✅ No high-risk fraud alerts at this time")
                
        except Exception as e:
            st.error(f"❌ Error loading alerts: {e}")
    else:
        st.info("🔌 Connect to the database to view real-time alerts")

# Tab 3: AI Chat Assistant
with tab3:
    st.markdown("## 💬 AI Fraud Analytics Assistant")
    
    if st.session_state.connected and st.session_state.mindsdb_client:
        # Quick action buttons
        st.markdown("### 🚀 Quick Insights")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 Fraud Summary", use_container_width=True):
                with st.spinner("Getting fraud summary..."):
                    response = st.session_state.mindsdb_client.get_fraud_summary()
                    st.session_state.chat_history.append({
                        "type": "assistant",
                        "message": response,
                        "timestamp": datetime.now()
                    })
        
        with col2:
            if st.button("📈 Fraud Trends", use_container_width=True):
                with st.spinner("Analyzing trends..."):
                    response = st.session_state.mindsdb_client.get_fraud_trends()
                    st.session_state.chat_history.append({
                        "type": "assistant",
                        "message": response,
                        "timestamp": datetime.now()
                    })
        
        with col3:
            if st.button("🚨 High Risk Alerts", use_container_width=True):
                with st.spinner("Getting alerts..."):
                    response = st.session_state.mindsdb_client.get_high_risk_alerts()
                    st.session_state.chat_history.append({
                        "type": "assistant",
                        "message": response,
                        "timestamp": datetime.now()
                    })
        
        with col4:
            if st.button("💡 Recommendations", use_container_width=True):
                with st.spinner("Getting recommendations..."):
                    response = st.session_state.mindsdb_client.get_fraud_prevention_recommendations()
                    st.session_state.chat_history.append({
                        "type": "assistant",
                        "message": response,
                        "timestamp": datetime.now()
                    })
        
        # Chat interface
        st.markdown("### 💬 Chat with AI Assistant")
        
        # Display chat history
        for chat in st.session_state.chat_history[-10:]:  # Show last 10 messages
            if chat["type"] == "user":
                st.markdown(f"""
                <div style="background-color: #e3f2fd; padding: 1rem; border-radius: 10px; margin: 1rem 0;">
                    <strong>You:</strong> {chat["message"]}<br>
                    <small>{chat["timestamp"].strftime('%H:%M:%S')}</small>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message">
                    <strong>🤖 AI Assistant:</strong><br>
                    {chat["message"]}<br>
                    <small>{chat["timestamp"].strftime('%H:%M:%S')}</small>
                </div>
                """, unsafe_allow_html=True)
        
        # Chat input
        user_question = st.text_input(
            "Ask the AI assistant about fraud patterns, trends, or specific cases:",
            placeholder="e.g., 'What are the most concerning fraud patterns today?'",
            key="chat_input"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📤 Send", type="primary", use_container_width=True):
                if user_question:
                    # Add user message
                    st.session_state.chat_history.append({
                        "type": "user",
                        "message": user_question,
                        "timestamp": datetime.now()
                    })
                    
                    # Get AI response
                    with st.spinner("AI is thinking..."):
                        response = st.session_state.mindsdb_client.query_agent(user_question)
                        st.session_state.chat_history.append({
                            "type": "assistant",
                            "message": response,
                            "timestamp": datetime.now()
                        })
                    
                    st.rerun()
        
        with col2:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
    else:
        st.info("🔌 Connect to the MindsDB agent to start chatting with the AI assistant")
        st.markdown("""
        **The AI assistant can help you with:**
        - 📊 Real-time fraud analysis and trends
        - 🔍 Pattern recognition and insights
        - 💡 Prevention strategies and recommendations
        - 🚨 Risk assessment for specific orders or users
        - 📈 Performance metrics and reporting
        """)

# Tab 4: Order Search
with tab4:
    st.markdown("## 🔍 Order Search & Analysis")
    
    if st.session_state.data_service:
        # Search interface
        col1, col2 = st.columns([2, 1])
        
        with col1:
            search_type = st.selectbox(
                "Search Type",
                ["Order ID", "User ID", "Fraud Score Range"]
            )
        
        with col2:
            if search_type == "Order ID":
                search_value = st.text_input("Enter Order ID")
            elif search_type == "User ID":
                search_value = st.text_input("Enter User ID")
            else:
                col_min, col_max = st.columns(2)
                with col_min:
                    min_score = st.number_input("Min Score", 0.0, 1.0, 0.5)
                with col_max:
                    max_score = st.number_input("Max Score", 0.0, 1.0, 1.0)
        
        if st.button("🔍 Search", type="primary"):
            try:
                if search_type == "Order ID" and search_value:
                    # Search specific order
                    with st.spinner("Searching for order..."):
                        order_details = st.session_state.data_service.get_order_details(search_value)
                    
                    if order_details:
                        st.success(f"✅ Found order: {search_value}")
                        
                        # Display order details in an organized way
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("### 📋 Order Information")
                            st.write(f"**Order ID:** {order_details['order_id']}")
                            st.write(f"**User ID:** {order_details['user_id']}")
                            st.write(f"**Amount:** ${order_details['total_amount']:.2f}")
                            st.write(f"**Payment Method:** {order_details['payment_method']}")
                            st.write(f"**Created:** {order_details['created_at']}")
                        
                        with col2:
                            st.markdown("### 🎯 Fraud Analysis")
                            st.write(f"**Fraud Score:** {order_details['spark_fraud_score']:.3f}")
                            st.write(f"**Risk Level:** {order_details['fraud_prediction']}")
                            st.write(f"**Priority:** {order_details['priority_level']}")
                            st.write(f"**Agent Required:** {order_details['requires_agent_analysis']}")
                        
                        # Show fraud reasons if available
                        if order_details['fraud_reasons']:
                            st.markdown("### ⚠️ Fraud Indicators")
                            fraud_reasons = order_details['fraud_reasons']
                            if isinstance(fraud_reasons, str):
                                try:
                                    fraud_reasons = json.loads(fraud_reasons.replace("'", '"'))
                                except:
                                    fraud_reasons = [fraud_reasons]
                            
                            for reason in fraud_reasons:
                                st.write(f"• {reason}")
                        
                        # Show agent analysis if available
                        if pd.notna(order_details.get('agent_fraud_score')):
                            st.markdown("### 🤖 Agent Analysis")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**Agent Score:** {order_details['agent_fraud_score']:.3f}")
                                st.write(f"**Recommendation:** {order_details['agent_recommended_action']}")
                                st.write(f"**Confidence:** {order_details.get('agent_confidence', 'N/A')}")
                            
                            with col2:
                                st.write(f"**Framework:** {order_details['agent_framework']}")
                                st.write(f"**Processing Time:** {order_details.get('agent_processing_time', 'N/A')}ms")
                                st.write(f"**Analysis Date:** {order_details.get('agent_analysis_time', 'N/A')}")
                            
                            if order_details.get('agent_reasoning'):
                                st.markdown("**AI Reasoning:**")
                                st.info(order_details['agent_reasoning'])
                    else:
                        st.warning(f"❌ Order {search_value} not found")
                
                elif search_type == "User ID" and search_value:
                    # Search user fraud history
                    with st.spinner("Loading user fraud history..."):
                        user_history = st.session_state.data_service.get_user_fraud_history(search_value)
                    
                    if user_history is not None and len(user_history) > 0:
                        st.success(f"✅ Found {len(user_history)} orders for user {search_value}")
                        
                        # User summary metrics
                        avg_score = user_history['spark_fraud_score'].mean()
                        high_risk_count = len(user_history[user_history['fraud_prediction'] == 'HIGH_RISK'])
                        total_amount = user_history['total_amount'].sum()
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Orders", len(user_history))
                        with col2:
                            st.metric("High Risk Orders", high_risk_count)
                        with col3:
                            st.metric("Avg Fraud Score", f"{avg_score:.3f}")
                        
                        # Display order history
                        st.dataframe(
                            user_history[['order_id', 'total_amount', 'spark_fraud_score', 
                                        'fraud_prediction', 'created_at']].head(20),
                            use_container_width=True
                        )
                    else:
                        st.warning(f"❌ No orders found for user {search_value}")
                
                elif search_type == "Fraud Score Range":
                    # Search by fraud score range
                    with st.spinner("Searching orders by fraud score..."):
                        results = st.session_state.data_service.search_orders_by_criteria(
                            fraud_score_min=min_score,
                            fraud_score_max=max_score,
                            limit=50
                        )
                    
                    if results is not None and len(results) > 0:
                        st.success(f"✅ Found {len(results)} orders with fraud score between {min_score} and {max_score}")
                        st.dataframe(results, use_container_width=True)
                    else:
                        st.warning("❌ No orders found in the specified fraud score range")
                        
            except Exception as e:
                st.error(f"❌ Search error: {e}")
    else:
        st.info("🔌 Connect to the database to search orders")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    🔍 UberEats Fraud Detection System | Built with Streamlit + MindsDB + PostgreSQL<br>
    Real-time fraud monitoring and AI-powered analytics
</div>
""", unsafe_allow_html=True)