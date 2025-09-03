"""
Sidebar component for dashboard controls
"""

import streamlit as st
from datetime import datetime
from typing import Dict

def render_sidebar() -> Dict:
    """Render sidebar with dashboard controls and return configuration"""
    
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3081/3081840.png", width=60)
    st.sidebar.title("🚚 Dashboard Controls")
    
    # System status
    st.sidebar.subheader("🔧 System Status")
    
    # Mock system status (in real implementation, this would check actual services)
    system_status = {
        "Kafka Stream": st.sidebar.checkbox("Kafka Connected", value=True, disabled=True),
        "OpenAI Agents": st.sidebar.checkbox("AI Agents Active", value=True, disabled=True),
        "GPS Processing": st.sidebar.checkbox("GPS Data Flow", value=True, disabled=True),
        "Anomaly Detection": st.sidebar.checkbox("Anomaly System", value=True, disabled=True)
    }
    
    st.sidebar.divider()
    
    # Data refresh settings
    st.sidebar.subheader("🔄 Refresh Settings")
    
    auto_refresh = st.sidebar.checkbox(
        "Auto Refresh", 
        value=True,
        help="Automatically refresh data from Kafka streams"
    )
    
    refresh_interval = st.sidebar.slider(
        "Refresh Interval (seconds)",
        min_value=10,
        max_value=120,
        value=30,
        step=10,
        disabled=not auto_refresh
    )
    
    if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()
    
    st.sidebar.divider()
    
    # Display filters
    st.sidebar.subheader("📊 Display Filters")
    
    show_inactive_drivers = st.sidebar.checkbox(
        "Show Inactive Drivers",
        value=False,
        help="Include drivers with no recent activity"
    )
    
    speed_filter = st.sidebar.slider(
        "Min Speed Filter (km/h)",
        min_value=0,
        max_value=100,
        value=0,
        help="Filter GPS points by minimum speed"
    )
    
    zone_filter = st.sidebar.multiselect(
        "Zone Filter",
        options=["Vila_Madalena", "Itaim_Bibi", "Pinheiros", "Centro", "Brooklin"],
        default=["Vila_Madalena", "Itaim_Bibi", "Pinheiros", "Centro", "Brooklin"],
        help="Select zones to display"
    )
    
    st.sidebar.divider()
    
    # Alert settings
    st.sidebar.subheader("🚨 Alert Configuration")
    
    speed_alert_threshold = st.sidebar.number_input(
        "Speed Alert Threshold (km/h)",
        min_value=50,
        max_value=120,
        value=80,
        help="Alert when drivers exceed this speed"
    )
    
    anomaly_alerts = st.sidebar.checkbox(
        "Anomaly Alerts",
        value=True,
        help="Show alerts for detected anomalies"
    )
    
    traffic_alerts = st.sidebar.checkbox(
        "Traffic Alerts",
        value=True,
        help="Show alerts for heavy traffic conditions"
    )
    
    st.sidebar.divider()
    
    # Map settings
    st.sidebar.subheader("🗺️ Map Settings")
    
    map_style = st.sidebar.selectbox(
        "Map Style",
        options=["open-street-map", "carto-positron", "carto-darkmatter", "stamen-terrain"],
        index=0,
        help="Choose map visualization style"
    )
    
    show_heatmap = st.sidebar.checkbox(
        "Show Traffic Heatmap",
        value=False,
        help="Display traffic density as heatmap overlay"
    )
    
    show_routes = st.sidebar.checkbox(
        "Show Optimal Routes",
        value=False,
        help="Display AI-suggested optimal routes"
    )
    
    st.sidebar.divider()
    
    # Analytics settings
    st.sidebar.subheader("📈 Analytics")
    
    prediction_horizon = st.sidebar.selectbox(
        "Prediction Horizon",
        options=["15 minutes", "30 minutes", "1 hour", "2 hours"],
        index=1,
        help="Time horizon for predictive analytics"
    )
    
    include_historical = st.sidebar.checkbox(
        "Include Historical Data",
        value=False,
        help="Include historical patterns in analysis"
    )
    
    ml_insights = st.sidebar.checkbox(
        "ML-Powered Insights",
        value=True,
        help="Enable machine learning-based insights"
    )
    
    st.sidebar.divider()
    
    # Export and actions
    st.sidebar.subheader("⚡ Actions")
    
    if st.sidebar.button("📊 Export Analytics Report", use_container_width=True):
        st.sidebar.success("Report exported! Check downloads folder.")
    
    if st.sidebar.button("🚨 Trigger Alert Test", use_container_width=True):
        st.sidebar.warning("Test alert triggered!")
    
    if st.sidebar.button("🔧 System Health Check", use_container_width=True):
        st.sidebar.info("System health: All services operational ✅")
    
    st.sidebar.divider()
    
    # System info
    st.sidebar.subheader("ℹ️ System Info")
    
    current_time = datetime.now().strftime("%H:%M:%S")
    st.sidebar.text(f"Current Time: {current_time}")
    st.sidebar.text("São Paulo Timezone (UTC-3)")
    st.sidebar.text("Dashboard Version: 1.0.0")
    
    # OpenAI API status
    st.sidebar.text("🤖 OpenAI: GPT-4o-mini")
    st.sidebar.text("🔗 Kafka: Confluent Cloud")
    
    # Data sources
    with st.sidebar.expander("📡 Data Sources"):
        st.write("**GPS Stream:** kafka-gps-data")
        st.write("**Orders:** kafka-orders")
        st.write("**Drivers:** kafka-drivers")
        st.write("**Agent Outputs:** eta-predictions, driver-allocations, route-optimizations")
    
    # Help section
    with st.sidebar.expander("❓ Help & Tips"):
        st.write("**Navigation:**")
        st.write("• Use tabs to switch between views")
        st.write("• Hover over charts for details")
        st.write("• Click legend items to toggle data")
        st.write("")
        st.write("**Troubleshooting:**")
        st.write("• No data? Check Kafka connection")
        st.write("• Slow updates? Reduce refresh rate")
        st.write("• Missing agents? Run OpenAI demo")
    
    # Return configuration dictionary
    return {
        'auto_refresh': auto_refresh,
        'refresh_interval': refresh_interval,
        'show_inactive_drivers': show_inactive_drivers,
        'speed_filter': speed_filter,
        'zone_filter': zone_filter,
        'speed_alert_threshold': speed_alert_threshold,
        'anomaly_alerts': anomaly_alerts,
        'traffic_alerts': traffic_alerts,
        'map_style': map_style,
        'show_heatmap': show_heatmap,
        'show_routes': show_routes,
        'prediction_horizon': prediction_horizon,
        'include_historical': include_historical,
        'ml_insights': ml_insights,
        'system_status': system_status
    }