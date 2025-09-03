"""
Real-time GPS map visualization component
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Optional

from interface.config.settings import DashboardConfig

def render_gps_map(gps_data: pd.DataFrame, config: Dict) -> None:
    """Render interactive GPS map with driver locations"""
    
    st.header("🗺️ Rastreamento GPS em Tempo Real")
    
    # Enhanced debugging and status display
    import logging
    logger = logging.getLogger(__name__)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("GPS Records", len(gps_data) if not gps_data.empty else 0)
    with col2:
        if not gps_data.empty and '_timestamp' in gps_data.columns:
            latest_time = gps_data['_timestamp'].max()
            time_ago = (datetime.now() - latest_time).total_seconds()
            st.metric("Latest Data", f"{int(time_ago)}s ago" if time_ago < 3600 else "1h+ ago")
        else:
            st.metric("Latest Data", "N/A")
    with col3:
        if not gps_data.empty and 'driver_id' in gps_data.columns:
            st.metric("Active Drivers", gps_data['driver_id'].nunique())
        else:
            st.metric("Active Drivers", 0)
    
    if gps_data.empty:
        st.warning("📍 Nenhum dado GPS disponível. Verifique:")
        st.info("🔍 1. Kafka consumer está conectado?")
        st.info("🔍 2. Dados GPS estão sendo enviados para 'kafka-gps-data'?")
        st.info("🔍 3. Clique em 'Forçar Atualização' no dashboard principal")
        
        # Show sample of expected data structure
        with st.expander("📊 Estrutura de dados esperada"):
            st.code("""
            {
                "driver_id": "abc123",
                "latitude": -23.5505,
                "longitude": -46.6333,
                "speed_kph": 15.5,
                "zone_name": "Vila_Madalena",
                "trip_stage": "idle",
                "traffic_density": "moderate"
            }
            """)
        return
    
    # Map controls
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    
    with col1:
        time_window = st.selectbox(
            "Janela de Tempo",
            options=[15, 30, 60, 120],
            index=1,
            format_func=lambda x: f"Últimos {x} minutos"
        )
    
    with col2:
        show_trails = st.checkbox("Mostrar Trilhas dos Motoristas", value=True)
    
    with col3:
        show_zones = st.checkbox("Mostrar Limites das Zonas", value=True)
    
    with col4:
        # Build color options based on available columns
        color_options = ["speed_kph", "zone_name", "trip_stage"]
        if not gps_data.empty and 'anomaly_flag' in gps_data.columns:
            color_options.append("anomaly_flag")
        
        color_by = st.selectbox(
            "Colorir Motoristas Por",
            options=color_options,
            index=0
        )
    
    # Filter data by time window
    cutoff_time = datetime.now() - timedelta(minutes=time_window)
    if '_timestamp' in gps_data.columns:
        recent_data = gps_data[gps_data['_timestamp'] >= cutoff_time].copy()
    else:
        recent_data = gps_data.copy()
    
    if recent_data.empty:
        st.warning(f"📍 No GPS data in the last {time_window} minutes.")
        return
    
    # Validate coordinates
    recent_data = recent_data.dropna(subset=['latitude', 'longitude'])
    
    if recent_data.empty:
        st.warning("📍 No valid GPS coordinates found.")
        return
    
    # Create the map
    dashboard_config = DashboardConfig()
    
    fig = go.Figure()
    
    # Add zone boundaries if enabled
    if show_zones:
        fig = _add_zone_boundaries(fig, dashboard_config)
    
    # Add driver locations
    fig = _add_driver_locations(fig, recent_data, color_by, dashboard_config)
    
    # Add driver trails if enabled
    if show_trails:
        fig = _add_driver_trails(fig, recent_data)
    
    # Update layout
    fig.update_layout(
        title={
            'text': f"🚚 Live Driver Locations - São Paulo ({len(recent_data)} GPS points)",
            'x': 0.5,
            'font': {'size': 20}
        },
        mapbox=dict(
            accesstoken=None,  # Use open street map
            style="open-street-map",
            center=dict(lat=dashboard_config.map_center_lat, lon=dashboard_config.map_center_lon),
            zoom=dashboard_config.map_zoom
        ),
        height=600,
        margin=dict(t=60, b=20, l=20, r=20),
        showlegend=True
    )
    
    # Display the map
    st.plotly_chart(fig, use_container_width=True)
    
    # Map statistics
    _display_map_statistics(recent_data)

def _add_zone_boundaries(fig: go.Figure, config: DashboardConfig) -> go.Figure:
    """Add São Paulo zone boundaries to the map"""
    
    # Simplified zone boundaries (in a real app, you'd load from a GeoJSON file)
    zone_boundaries = {
        'Vila_Madalena': {
            'lat': [-23.5358, -23.5558, -23.5458],
            'lon': [-46.6819, -46.7019, -46.6919]
        },
        'Itaim_Bibi': {
            'lat': [-23.5656, -23.5856, -23.5756],
            'lon': [-46.6714, -46.6914, -46.6814]
        },
        'Pinheiros': {
            'lat': [-23.5531, -23.5731, -23.5631],
            'lon': [-46.6919, -46.7119, -46.7019]
        }
    }
    
    for zone_name, coords in zone_boundaries.items():
        color = config.get_zone_color(zone_name)
        
        fig.add_trace(go.Scattermapbox(
            lat=coords['lat'] + [coords['lat'][0]],  # Close the polygon
            lon=coords['lon'] + [coords['lon'][0]],
            mode='lines',
            line=dict(width=2, color=color),
            name=f"Zone: {zone_name}",
            hoverinfo='text',
            hovertext=f"Zone: {zone_name.replace('_', ' ')}",
            showlegend=False
        ))
    
    return fig

def _add_driver_locations(fig: go.Figure, df: pd.DataFrame, color_by: str, config: DashboardConfig) -> go.Figure:
    """Add driver locations to the map"""
    
    # Get the most recent location for each driver
    if 'driver_id' in df.columns and '_timestamp' in df.columns:
        latest_positions = df.sort_values('_timestamp').groupby('driver_id').tail(1)
    else:
        latest_positions = df
    
    # Prepare hover text with Portuguese labels
    hover_template = "<b>Motorista:</b> %{customdata[0]}<br>"
    hover_template += "<b>Velocidade:</b> %{customdata[1]:.1f} km/h<br>"
    hover_template += "<b>Zona:</b> %{customdata[2]}<br>"
    hover_template += "<b>Estágio:</b> %{customdata[3]}<br>"
    hover_template += "<b>Horário:</b> %{customdata[4]}<br>"
    
    if 'anomaly_flag' in latest_positions.columns:
        hover_template += "<b>Anomalia:</b> %{customdata[5]}<br>"
    
    hover_template += "<extra></extra>"
    
    # Prepare custom data for hover
    custom_data = []
    for _, row in latest_positions.iterrows():
        driver_id = str(row.get('driver_id', 'Unknown'))[:12] + "..."
        speed = row.get('speed_kph', 0)
        zone = row.get('zone_name', 'Unknown').replace('_', ' ')
        stage = row.get('trip_stage', 'unknown')
        timestamp = row.get('_timestamp', 'Unknown')
        if isinstance(timestamp, str):
            timestamp = timestamp
        elif hasattr(timestamp, 'strftime'):
            timestamp = timestamp.strftime('%H:%M:%S')
        # Only include anomaly if column exists
        if 'anomaly_flag' in latest_positions.columns:
            anomaly = row.get('anomaly_flag', 'Nenhuma') or 'Nenhuma'
            custom_data.append([driver_id, speed, zone, stage, timestamp, anomaly])
        else:
            custom_data.append([driver_id, speed, zone, stage, timestamp])
    
    # Color mapping
    if color_by == "speed_kph":
        color_scale = "Viridis"
        color_values = latest_positions.get('speed_kph', [0] * len(latest_positions))
    elif color_by == "zone_name":
        # Map zones to colors
        zone_colors = {zone: i for i, zone in enumerate(latest_positions['zone_name'].unique())}
        color_values = latest_positions['zone_name'].map(zone_colors)
        color_scale = "Set3"
    elif color_by == "trip_stage":
        stage_colors = {
            'idle': 0, 'to_pickup': 1, 'at_pickup': 2, 
            'to_destination': 3, 'at_destination': 4, 'completed': 5
        }
        color_values = latest_positions['trip_stage'].map(stage_colors).fillna(0)
        color_scale = "Plotly3"
    elif color_by == "anomaly_flag" and 'anomaly_flag' in latest_positions.columns:
        color_values = latest_positions['anomaly_flag'].notna().astype(int)
        color_scale = [[0, "green"], [1, "red"]]
    else:
        color_values = [1] * len(latest_positions)
        color_scale = "Blues"
    
    # Add driver markers
    fig.add_trace(go.Scattermapbox(
        lat=latest_positions['latitude'],
        lon=latest_positions['longitude'],
        mode='markers',
        marker=dict(
            size=12,
            color=color_values,
            colorscale=color_scale,
            showscale=True,
            colorbar=dict(
                title=color_by.replace('_', ' ').title(),
                x=1.02
            ),
            opacity=0.8
        ),
        customdata=custom_data,
        hovertemplate=hover_template,
        name="Driver Locations",
        showlegend=False
    ))
    
    return fig

def _add_driver_trails(fig: go.Figure, df: pd.DataFrame) -> go.Figure:
    """Add driver movement trails to the map"""
    
    if 'driver_id' not in df.columns:
        return fig
    
    # Show trails for top 5 most active drivers to avoid clutter
    driver_activity = df['driver_id'].value_counts().head(5)
    
    colors = ['red', 'blue', 'green', 'purple', 'orange']
    
    for i, (driver_id, _) in enumerate(driver_activity.items()):
        driver_data = df[df['driver_id'] == driver_id].sort_values('_timestamp')
        
        if len(driver_data) < 2:
            continue
        
        fig.add_trace(go.Scattermapbox(
            lat=driver_data['latitude'],
            lon=driver_data['longitude'],
            mode='lines',
            line=dict(width=2, color=colors[i % len(colors)]),
            name=f"Trail: {str(driver_id)[:8]}...",
            opacity=0.6,
            showlegend=True,
            hoverinfo='skip'
        ))
    
    return fig

def _display_map_statistics(df: pd.DataFrame) -> None:
    """Display map and driver statistics"""
    
    st.subheader("📊 Map Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        active_drivers = df['driver_id'].nunique() if 'driver_id' in df.columns else 0
        st.metric("Active Drivers", active_drivers)
    
    with col2:
        zones_covered = df['zone_name'].nunique() if 'zone_name' in df.columns else 0
        st.metric("Zones Covered", zones_covered)
    
    with col3:
        avg_speed = df['speed_kph'].mean() if 'speed_kph' in df.columns else 0
        st.metric("Avg Speed", f"{avg_speed:.1f} km/h")
    
    with col4:
        anomalies = df['anomaly_flag'].notna().sum() if 'anomaly_flag' in df.columns else 0
        st.metric("Anomalias Detectadas", anomalies)
    
    # Zone activity breakdown
    if 'zone_name' in df.columns:
        st.subheader("🌍 Atividade por Zona")
        
        # Build aggregation dict based on available columns
        agg_dict = {
            'driver_id': 'nunique',
            'speed_kph': 'mean' if 'speed_kph' in df.columns else lambda x: 0
        }
        
        # Add anomaly column if it exists
        if 'anomaly_flag' in df.columns:
            agg_dict['anomaly_flag'] = lambda x: x.notna().sum()
            columns = ['Motoristas Únicos', 'Velocidade Média (km/h)', 'Anomalias']
        else:
            columns = ['Motoristas Únicos', 'Velocidade Média (km/h)']
        
        zone_stats = df.groupby('zone_name').agg(agg_dict).round(2)
        zone_stats.columns = columns
        zone_stats.index.name = 'Zona'
        
        # Sort by driver activity
        zone_stats = zone_stats.sort_values('Motoristas Únicos', ascending=False)
        
        st.dataframe(zone_stats, use_container_width=True)
    
    # Speed distribution
    if 'speed_kph' in df.columns:
        st.subheader("🚗 Distribuição de Velocidade")
        
        speed_data = df['speed_kph'].dropna()
        
        if not speed_data.empty:
            # Create speed histogram
            fig_speed = px.histogram(
                x=speed_data,
                nbins=20,
                title="Driver Speed Distribution",
                labels={'x': 'Speed (km/h)', 'y': 'Number of GPS Points'},
                color_discrete_sequence=['#FF6B35']
            )
            
            fig_speed.update_layout(
                height=300,
                showlegend=False,
                margin=dict(t=40, b=20, l=20, r=20)
            )
            
            st.plotly_chart(fig_speed, use_container_width=True)
            
            # Speed categories
            col1, col2, col3 = st.columns(3)
            
            with col1:
                stopped = len(speed_data[speed_data <= 5])
                st.metric("Stopped/Slow", stopped, help="≤ 5 km/h")
            
            with col2:
                normal = len(speed_data[(speed_data > 5) & (speed_data <= 50)])
                st.metric("Normal Speed", normal, help="5-50 km/h")
            
            with col3:
                fast = len(speed_data[speed_data > 50])
                st.metric("High Speed", fast, help="> 50 km/h")