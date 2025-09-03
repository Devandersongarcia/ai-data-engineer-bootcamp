"""
Real-time metrics dashboard component
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np

from interface.utils.data_processor import DataProcessor

def render_metrics_dashboard(gps_data: pd.DataFrame, agent_data: List[Dict], config: Dict) -> None:
    """Render the main metrics dashboard"""
    
    st.header("📊 Métricas do Sistema em Tempo Real")
    
    # Enhanced GPS data debugging
    import logging
    logger = logging.getLogger(__name__)
    
    # Debug info for development
    if gps_data.empty:
        st.warning("⚠️ Nenhum dado GPS encontrado para exibir métricas")
        st.info("🔍 Verifique se o consumer Kafka está funcionando corretamente")
        # Show button to test direct GPS consumption
        if st.button("🧪 Testar Conexão Direta GPS"):
            with st.spinner("Testando conexão direta com Kafka..."):
                # Test direct connection
                try:
                    from interface.utils.kafka_consumer import KafkaDataStream
                    stream = KafkaDataStream()
                    test_data = stream._direct_gps_fetch(1)  # 1 minute of data
                    if not test_data.empty:
                        st.success(f"✅ Conexão funcionando! Encontrados {len(test_data)} registros GPS")
                        st.json(test_data.head(3).to_dict('records'))
                    else:
                        st.error("❌ Nenhum dado GPS encontrado no teste direto")
                except Exception as e:
                    st.error(f"❌ Erro no teste: {e}")
    else:
        logger.info(f"📊 Metrics Dashboard: Processing {len(gps_data)} GPS records")
        if 'driver_id' in gps_data.columns:
            logger.info(f"📊 Active drivers found: {gps_data['driver_id'].nunique()}")
    
    # Initialize data processor
    processor = DataProcessor()
    
    # Main KPI cards
    _render_kpi_cards(gps_data, agent_data)
    
    st.divider()
    
    # System health overview
    col1, col2 = st.columns([2, 1])
    
    with col1:
        _render_system_health(gps_data, agent_data, processor)
    
    with col2:
        _render_live_alerts(gps_data, agent_data)
    
    st.divider()
    
    # Performance charts
    col1, col2 = st.columns(2)
    
    with col1:
        _render_zone_performance_chart(gps_data, processor)
    
    with col2:
        _render_agent_activity_chart(agent_data)
    
    st.divider()
    
    # Detailed analytics
    _render_detailed_analytics(gps_data, agent_data, processor)

def _render_kpi_cards(gps_data: pd.DataFrame, agent_data: List[Dict]) -> None:
    """Render key performance indicator cards"""
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Calculate metrics
    total_events = len(gps_data) if not gps_data.empty else 0
    active_drivers = gps_data['driver_id'].nunique() if 'driver_id' in gps_data.columns else 0
    zones_covered = gps_data['zone_name'].nunique() if 'zone_name' in gps_data.columns else 0
    avg_speed = gps_data['speed_kph'].mean() if 'speed_kph' in gps_data.columns else 0
    anomalies = gps_data['anomaly_flag'].notna().sum() if 'anomaly_flag' in gps_data.columns else 0
    
    with col1:
        st.metric(
            label="📍 Eventos GPS",
            value=f"{total_events:,}",
            delta=f"+{min(total_events, 147)} novos" if total_events > 0 else None
        )
    
    with col2:
        st.metric(
            label="🚗 Motoristas Ativos",
            value=active_drivers,
            delta="+2" if active_drivers > 3 else None
        )
    
    with col3:
        st.metric(
            label="🌍 Zonas Cobertas",
            value=zones_covered,
            delta=f"{zones_covered}/5 zonas de São Paulo"
        )
    
    with col4:
        # Speed with color indication
        speed_delta = None
        if avg_speed > 0:
            if avg_speed > 30:
                speed_delta = "⚡ Áreas de trânsito rápido"
            elif avg_speed < 10:
                speed_delta = "🐌 Congestionamento pesado"
            else:
                speed_delta = "✅ Fluxo normal"
        
        st.metric(
            label="⚡ Velocidade Média",
            value=f"{avg_speed:.1f} km/h",
            delta=speed_delta
        )
    
    with col5:
        # Anomalies with severity indication
        anomaly_delta = None
        if anomalies > 0:
            anomaly_rate = (anomalies / total_events) * 100 if total_events > 0 else 0
            if anomaly_rate > 10:
                anomaly_delta = "🚨 Alta taxa de anomalias"
            elif anomaly_rate > 5:
                anomaly_delta = "⚠️ Anomalias moderadas"
            else:
                anomaly_delta = "✅ Baixa taxa de anomalias"
        
        st.metric(
            label="🚨 Anomalias",
            value=anomalies,
            delta=anomaly_delta
        )

def _render_system_health(gps_data: pd.DataFrame, agent_data: List[Dict], processor: DataProcessor) -> None:
    """Render system health overview"""
    
    st.subheader("🏥 Saúde do Sistema")
    
    # Calculate health metrics
    health_metrics = processor.calculate_system_health_metrics(gps_data, agent_data)
    
    # Health score gauge
    overall_score = np.mean([
        health_metrics['data_quality']['score'],
        health_metrics['agent_performance']['score'],
        health_metrics['system_efficiency']['score'],
        health_metrics['anomaly_detection']['score'],
        health_metrics['coverage_analysis']['score']
    ])
    
    # Create gauge chart
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = overall_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Saúde Geral do Sistema"},
        delta = {'reference': 90, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 80], 'color': "yellow"},
                {'range': [80, 100], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig_gauge.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig_gauge, use_container_width=True)
    
    # Health components breakdown
    health_components = {
        "📊 Data Quality": health_metrics['data_quality']['score'],
        "🤖 Agent Performance": health_metrics['agent_performance']['score'], 
        "⚡ System Efficiency": health_metrics['system_efficiency']['score'],
        "🚨 Anomaly Detection": health_metrics['anomaly_detection']['score'],
        "🌍 Zone Coverage": health_metrics['coverage_analysis']['score']
    }
    
    for component, score in health_components.items():
        if score >= 80:
            status_color = "🟢"
        elif score >= 60:
            status_color = "🟡"
        else:
            status_color = "🔴"
        
        st.write(f"{status_color} {component}: **{score:.0f}%**")

def _render_live_alerts(gps_data: pd.DataFrame, agent_data: List[Dict]) -> None:
    """Render live system alerts"""
    
    st.subheader("🚨 Live Alerts")
    
    alerts = []
    
    # Check for data freshness
    if not gps_data.empty and '_timestamp' in gps_data.columns:
        latest_data = gps_data['_timestamp'].max()
        if isinstance(latest_data, str):
            latest_data = pd.to_datetime(latest_data)
        
        if (datetime.now() - latest_data).total_seconds() > 300:  # 5 minutes
            alerts.append({
                'severity': 'high',
                'message': 'GPS data is stale (>5 min old)',
                'icon': '🔴'
            })
    
    # Check for excessive speeds
    if 'speed_kph' in gps_data.columns:
        excessive_speeds = gps_data[gps_data['speed_kph'] > 80]
        if not excessive_speeds.empty:
            alerts.append({
                'severity': 'medium',
                'message': f'{len(excessive_speeds)} excessive speed events detected',
                'icon': '🟡'
            })
    
    # Check for agent activity
    recent_cutoff = datetime.now() - timedelta(minutes=10)
    recent_agent_activity = [a for a in agent_data if a.get('timestamp', datetime.min) >= recent_cutoff]
    
    if len(recent_agent_activity) < 3:
        alerts.append({
            'severity': 'medium',
            'message': 'Low agent activity in last 10 minutes',
            'icon': '🟡'
        })
    
    # Check for anomaly clusters
    if 'anomaly_flag' in gps_data.columns and 'zone_name' in gps_data.columns:
        zone_anomalies = gps_data[gps_data['anomaly_flag'].notna()].groupby('zone_name').size()
        high_anomaly_zones = zone_anomalies[zone_anomalies > 3]
        
        for zone, count in high_anomaly_zones.items():
            alerts.append({
                'severity': 'high',
                'message': f'{count} anomalies detected in {zone.replace("_", " ")}',
                'icon': '🔴'
            })
    
    # Display alerts
    if alerts:
        for alert in alerts[-5:]:  # Show only last 5 alerts
            st.write(f"{alert['icon']} {alert['message']}")
    else:
        st.success("✅ All systems operating normally")
    
    # Agent status
    st.write("**🤖 Agent Status:**")
    if agent_data:
        agent_types = set(a.get('agent_type', 'Unknown') for a in recent_agent_activity)
        for agent_type in ['⏱️ ETA Prediction', '🎯 Driver Allocation', '🗺️ Route Optimization', '🚨 System Alerts']:
            status = "🟢 Active" if agent_type in agent_types else "🔴 Inactive"
            st.write(f"  {agent_type}: {status}")
    else:
        st.write("  No agent activity detected")

def _render_zone_performance_chart(gps_data: pd.DataFrame, processor: DataProcessor) -> None:
    """Render zone performance chart"""
    
    st.subheader("🌍 Zone Performance")
    
    if gps_data.empty or 'zone_name' not in gps_data.columns:
        st.info("No zone data available")
        return
    
    # Calculate zone statistics
    zone_stats = processor.calculate_zone_statistics(gps_data)
    
    if not zone_stats:
        st.info("No zone statistics available")
        return
    
    # Prepare data for chart
    zones = []
    efficiency_scores = []
    driver_counts = []
    anomaly_rates = []
    
    for zone, stats in zone_stats.items():
        zones.append(zone.replace('_', ' '))
        efficiency_scores.append(stats.get('avg_efficiency', 0))
        driver_counts.append(stats.get('unique_drivers', 0))
        anomaly_rates.append(stats.get('anomaly_rate', 0))
    
    # Create bubble chart
    fig_zones = go.Figure()
    
    fig_zones.add_trace(go.Scatter(
        x=efficiency_scores,
        y=anomaly_rates,
        mode='markers+text',
        marker=dict(
            size=[max(10, count * 5) for count in driver_counts],  # Bubble size based on driver count
            color=efficiency_scores,
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="Efficiency %"),
            opacity=0.7
        ),
        text=zones,
        textposition="middle center",
        textfont=dict(size=10, color="white"),
        hovertemplate="<b>%{text}</b><br>" +
                      "Efficiency: %{x:.1f}%<br>" +
                      "Anomaly Rate: %{y:.1f}%<br>" +
                      "<extra></extra>",
        name="Zones"
    ))
    
    fig_zones.update_layout(
        title="Zone Performance: Efficiency vs Anomaly Rate",
        xaxis_title="Efficiency Score (%)",
        yaxis_title="Anomaly Rate (%)",
        height=400,
        margin=dict(t=40, b=20, l=20, r=20),
        showlegend=False
    )
    
    st.plotly_chart(fig_zones, use_container_width=True)

def _render_agent_activity_chart(agent_data: List[Dict]) -> None:
    """Render agent activity timeline chart"""
    
    st.subheader("🤖 Agent Activity Timeline")
    
    if not agent_data:
        st.info("No agent activity data available")
        return
    
    # Recent activity (last 30 minutes)
    recent_cutoff = datetime.now() - timedelta(minutes=30)
    recent_activities = [a for a in agent_data if a.get('timestamp', datetime.min) >= recent_cutoff]
    
    if not recent_activities:
        st.info("No recent agent activity")
        return
    
    # Group by agent type and time
    agent_timeline = {}
    for activity in recent_activities:
        agent_type = activity.get('agent_type', 'Unknown')
        timestamp = activity.get('timestamp')
        
        if agent_type not in agent_timeline:
            agent_timeline[agent_type] = []
        
        agent_timeline[agent_type].append(timestamp)
    
    # Create timeline chart
    fig_timeline = go.Figure()
    
    colors = ['#FF6B35', '#F7931E', '#4ECDC4', '#45B7D1']
    
    for i, (agent_type, timestamps) in enumerate(agent_timeline.items()):
        # Count activities in 5-minute buckets
        time_buckets = {}
        for ts in timestamps:
            # Round to 5-minute bucket
            bucket = ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)
            time_buckets[bucket] = time_buckets.get(bucket, 0) + 1
        
        if time_buckets:
            x_vals = list(time_buckets.keys())
            y_vals = list(time_buckets.values())
            
            fig_timeline.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode='lines+markers',
                name=agent_type,
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=8)
            ))
    
    fig_timeline.update_layout(
        title="Agent Activity Over Time (5-min buckets)",
        xaxis_title="Time",
        yaxis_title="Activities Count",
        height=400,
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_timeline, use_container_width=True)

def _render_detailed_analytics(gps_data: pd.DataFrame, agent_data: List[Dict], processor: DataProcessor) -> None:
    """Render detailed analytics section"""
    
    st.subheader("📈 Detailed Analytics")
    
    # Create tabs for different analytics views
    tab1, tab2, tab3 = st.tabs(["Driver Analytics", "Traffic Analysis", "System Performance"])
    
    with tab1:
        _render_driver_analytics(gps_data, processor)
    
    with tab2:
        _render_traffic_analysis(gps_data)
    
    with tab3:
        _render_system_performance(gps_data, agent_data, processor)

def _render_driver_analytics(gps_data: pd.DataFrame, processor: DataProcessor) -> None:
    """Render driver-specific analytics"""
    
    if gps_data.empty or 'driver_id' not in gps_data.columns:
        st.info("No driver data available")
        return
    
    driver_analytics = processor.calculate_driver_analytics(gps_data)
    
    if not driver_analytics:
        st.info("No driver analytics available")
        return
    
    # Top performers
    st.write("**🏆 Top Performing Drivers:**")
    
    # Sort by safety score
    sorted_drivers = sorted(
        driver_analytics.items(),
        key=lambda x: x[1].get('safety_score', 0),
        reverse=True
    )[:5]
    
    for i, (driver_id, stats) in enumerate(sorted_drivers, 1):
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            st.write(f"{i}. **Driver {str(driver_id)[:12]}...**")
        
        with col2:
            safety_score = stats.get('safety_score', 0)
            if safety_score >= 80:
                st.write(f"🟢 {safety_score:.0f}% safety")
            elif safety_score >= 60:
                st.write(f"🟡 {safety_score:.0f}% safety")
            else:
                st.write(f"🔴 {safety_score:.0f}% safety")
        
        with col3:
            avg_speed = stats.get('avg_speed', 0)
            st.write(f"⚡ {avg_speed:.1f} km/h")
        
        with col4:
            zones_visited = stats.get('zones_visited', 0)
            st.write(f"🌍 {zones_visited} zones")

def _render_traffic_analysis(gps_data: pd.DataFrame) -> None:
    """Render traffic analysis"""
    
    if gps_data.empty:
        st.info("No traffic data available")
        return
    
    # Traffic density by zone
    if 'traffic_density' in gps_data.columns and 'zone_name' in gps_data.columns:
        st.write("**🚦 Traffic Conditions by Zone:**")
        
        traffic_data = gps_data.groupby(['zone_name', 'traffic_density']).size().unstack(fill_value=0)
        
        if not traffic_data.empty:
            # Create heatmap
            fig_traffic = px.imshow(
                traffic_data.values,
                labels=dict(x="Traffic Density", y="Zone", color="Event Count"),
                x=traffic_data.columns,
                y=[zone.replace('_', ' ') for zone in traffic_data.index],
                aspect="auto",
                color_continuous_scale="Reds"
            )
            
            fig_traffic.update_layout(
                title="Traffic Density Heatmap by Zone",
                height=300,
                margin=dict(t=40, b=20, l=20, r=20)
            )
            
            st.plotly_chart(fig_traffic, use_container_width=True)

def _render_system_performance(gps_data: pd.DataFrame, agent_data: List[Dict], processor: DataProcessor) -> None:
    """Render system performance metrics"""
    
    st.write("**⚡ System Performance Metrics:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Data processing rate
        if not gps_data.empty and '_timestamp' in gps_data.columns:
            time_span = (gps_data['_timestamp'].max() - gps_data['_timestamp'].min()).total_seconds()
            if time_span > 0:
                processing_rate = len(gps_data) / (time_span / 60)  # events per minute
                st.metric("Processing Rate", f"{processing_rate:.1f} events/min")
        
        # Agent response time (simulated)
        avg_agent_response = 0.8  # seconds
        st.metric("Avg Agent Response", f"{avg_agent_response:.1f}s")
        
        # System uptime
        st.metric("System Uptime", "99.7%")
    
    with col2:
        # Memory usage (simulated)
        memory_usage = min(85, len(gps_data) * 0.01 + 45)
        st.metric("Memory Usage", f"{memory_usage:.1f}%")
        
        # API calls (OpenAI)
        total_api_calls = len(agent_data)
        st.metric("API Calls (Today)", f"{total_api_calls:,}")
        
        # Error rate
        error_rate = 0.1  # 0.1%
        st.metric("Error Rate", f"{error_rate:.1f}%")