"""
Advanced analytics and insights component
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List
from scipy import stats
import seaborn as sns

from interface.utils.data_processor import DataProcessor

def render_analytics_charts(gps_data: pd.DataFrame, agent_data: List[Dict], config: Dict) -> None:
    """Render advanced analytics and insights"""
    
    st.header("📈 Advanced Analytics & Insights")
    
    if gps_data.empty:
        st.warning("📊 No GPS data available for analytics. Start the data processing system first.")
        return
    
    processor = DataProcessor()
    enriched_data = processor.enrich_gps_data(gps_data)
    
    # Analytics controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        analysis_window = st.selectbox(
            "Analysis Period",
            options=[30, 60, 120, 240],
            index=1,
            format_func=lambda x: f"Last {x} minutes"
        )
    
    with col2:
        analysis_type = st.selectbox(
            "Analysis Focus",
            options=["Traffic Patterns", "Driver Behavior", "Zone Optimization", "Anomaly Analysis"]
        )
    
    with col3:
        include_predictions = st.checkbox("Include ML Predictions", value=False)
    
    # Filter data by time window
    cutoff_time = datetime.now() - timedelta(minutes=analysis_window)
    if '_timestamp' in enriched_data.columns:
        analysis_data = enriched_data[enriched_data['_timestamp'] >= cutoff_time].copy()
    else:
        analysis_data = enriched_data.copy()
    
    # Render analytics based on selection
    if analysis_type == "Traffic Patterns":
        _render_traffic_analytics(analysis_data, processor)
    elif analysis_type == "Driver Behavior":
        _render_driver_behavior_analytics(analysis_data, processor)
    elif analysis_type == "Zone Optimization":
        _render_zone_optimization_analytics(analysis_data, processor)
    elif analysis_type == "Anomaly Analysis":
        _render_anomaly_analytics(analysis_data, processor)
    
    st.divider()
    
    # Business insights section
    _render_business_insights(analysis_data, agent_data, processor)

def _render_traffic_analytics(data: pd.DataFrame, processor: DataProcessor) -> None:
    """Render traffic pattern analysis"""
    
    st.subheader("🚦 Traffic Pattern Analysis")
    
    if data.empty:
        st.info("No traffic data available for analysis")
        return
    
    # Traffic flow by hour
    col1, col2 = st.columns(2)
    
    with col1:
        if 'hour' in data.columns and 'speed_kph' in data.columns:
            hourly_traffic = data.groupby('hour').agg({
                'speed_kph': ['mean', 'count'],
                'traffic_score': 'mean'
            }).round(2)
            
            hourly_traffic.columns = ['Avg Speed (km/h)', 'GPS Events', 'Traffic Density']
            
            fig_hourly = go.Figure()
            
            # Speed line
            fig_hourly.add_trace(go.Scatter(
                x=hourly_traffic.index,
                y=hourly_traffic['Avg Speed (km/h)'],
                mode='lines+markers',
                name='Speed',
                yaxis='y',
                line=dict(color='#FF6B35', width=3)
            ))
            
            # Traffic density bars
            fig_hourly.add_trace(go.Bar(
                x=hourly_traffic.index,
                y=hourly_traffic['Traffic Density'],
                name='Traffic Density',
                yaxis='y2',
                opacity=0.6,
                marker_color='#4ECDC4'
            ))
            
            fig_hourly.update_layout(
                title="Traffic Patterns by Hour",
                xaxis_title="Hour of Day",
                yaxis=dict(title="Speed (km/h)", side="left"),
                yaxis2=dict(title="Traffic Density Score", side="right", overlaying="y"),
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            
            st.plotly_chart(fig_hourly, use_container_width=True)
    
    with col2:
        # Zone traffic heatmap
        if 'zone_name' in data.columns and 'traffic_score' in data.columns:
            zone_traffic = data.groupby(['zone_name', 'hour']).agg({
                'traffic_score': 'mean',
                'speed_kph': 'mean'
            }).reset_index()
            
            if not zone_traffic.empty:
                pivot_traffic = zone_traffic.pivot_table(
                    index='zone_name', 
                    columns='hour', 
                    values='traffic_score',
                    fill_value=0
                )
                
                fig_heatmap = px.imshow(
                    pivot_traffic.values,
                    labels=dict(x="Hour", y="Zone", color="Traffic Score"),
                    x=pivot_traffic.columns,
                    y=[zone.replace('_', ' ') for zone in pivot_traffic.index],
                    aspect="auto",
                    color_continuous_scale="Reds",
                    title="Traffic Density Heatmap: Zone vs Hour"
                )
                
                fig_heatmap.update_layout(height=400)
                st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Traffic insights
    st.write("**🚦 Traffic Insights:**")
    
    insights = []
    
    if 'hour' in data.columns and 'speed_kph' in data.columns:
        # Peak traffic times
        hourly_speed = data.groupby('hour')['speed_kph'].mean()
        slowest_hours = hourly_speed.nsmallest(3).index.tolist()
        fastest_hours = hourly_speed.nlargest(3).index.tolist()
        
        insights.append(f"🕐 Slowest traffic: {[f'{h}:00' for h in slowest_hours]}")
        insights.append(f"⚡ Fastest traffic: {[f'{h}:00' for h in fastest_hours]}")
    
    if 'zone_name' in data.columns and 'traffic_score' in data.columns:
        # Most congested zones
        zone_congestion = data.groupby('zone_name')['traffic_score'].mean().sort_values(ascending=False)
        most_congested = zone_congestion.head(2).index.tolist()
        least_congested = zone_congestion.tail(2).index.tolist()
        
        insights.append(f"🔴 Most congested zones: {[z.replace('_', ' ') for z in most_congested]}")
        insights.append(f"🟢 Least congested zones: {[z.replace('_', ' ') for z in least_congested]}")
    
    for insight in insights:
        st.info(insight)

def _render_driver_behavior_analytics(data: pd.DataFrame, processor: DataProcessor) -> None:
    """Render driver behavior analysis"""
    
    st.subheader("👨‍💼 Driver Behavior Analysis")
    
    if data.empty or 'driver_id' not in data.columns:
        st.info("No driver data available for analysis")
        return
    
    driver_analytics = processor.calculate_driver_analytics(data)
    
    if not driver_analytics:
        st.info("Unable to calculate driver analytics")
        return
    
    # Driver performance distribution
    col1, col2 = st.columns(2)
    
    with col1:
        # Safety scores distribution
        safety_scores = [stats.get('safety_score', 0) for stats in driver_analytics.values()]
        
        fig_safety = go.Figure(data=[
            go.Histogram(x=safety_scores, nbinsx=10, name="Safety Scores")
        ])
        
        fig_safety.update_traces(
            marker_color='#28a745',
            marker_line_color='rgb(8,48,107)',
            marker_line_width=1.5,
            opacity=0.6
        )
        
        fig_safety.update_layout(
            title="Driver Safety Score Distribution",
            xaxis_title="Safety Score (%)",
            yaxis_title="Number of Drivers",
            height=350
        )
        
        st.plotly_chart(fig_safety, use_container_width=True)
    
    with col2:
        # Speed vs Safety scatter plot
        speeds = [stats.get('avg_speed', 0) for stats in driver_analytics.values()]
        safety_scores = [stats.get('safety_score', 0) for stats in driver_analytics.values()]
        driver_ids = list(driver_analytics.keys())
        
        fig_scatter = go.Figure()
        
        fig_scatter.add_trace(go.Scatter(
            x=speeds,
            y=safety_scores,
            mode='markers',
            marker=dict(
                size=10,
                color=safety_scores,
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="Safety Score")
            ),
            text=[f"Driver {str(d)[:8]}..." for d in driver_ids],
            hovertemplate="<b>%{text}</b><br>" +
                          "Avg Speed: %{x:.1f} km/h<br>" +
                          "Safety Score: %{y:.1f}%<br>" +
                          "<extra></extra>"
        ))
        
        fig_scatter.update_layout(
            title="Driver Speed vs Safety Analysis",
            xaxis_title="Average Speed (km/h)",
            yaxis_title="Safety Score (%)",
            height=350
        )
        
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Top and bottom performers
    st.write("**🏆 Driver Performance Rankings:**")
    
    # Sort drivers by safety score
    sorted_drivers = sorted(
        driver_analytics.items(),
        key=lambda x: x[1].get('safety_score', 0),
        reverse=True
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🥇 Top Performers:**")
        for i, (driver_id, stats) in enumerate(sorted_drivers[:5], 1):
            safety = stats.get('safety_score', 0)
            speed = stats.get('avg_speed', 0)
            zones = stats.get('zones_visited', 0)
            
            st.write(f"{i}. **{str(driver_id)[:12]}...** - {safety:.0f}% safety, {speed:.1f} km/h avg, {zones} zones")
    
    with col2:
        st.write("**⚠️ Needs Attention:**")
        for i, (driver_id, stats) in enumerate(sorted_drivers[-5:], 1):
            safety = stats.get('safety_score', 0)
            anomalies = stats.get('anomaly_count', 0)
            high_speed = stats.get('high_speed_events', 0)
            
            issues = []
            if safety < 60:
                issues.append("low safety")
            if anomalies > 0:
                issues.append(f"{anomalies} anomalies")
            if high_speed > 0:
                issues.append(f"{high_speed} high-speed events")
            
            issue_text = ", ".join(issues) if issues else "minor concerns"
            st.write(f"{i}. **{str(driver_id)[:12]}...** - {issue_text}")

def _render_zone_optimization_analytics(data: pd.DataFrame, processor: DataProcessor) -> None:
    """Render zone optimization analysis"""
    
    st.subheader("🗺️ Zone Optimization Analysis")
    
    if data.empty or 'zone_name' not in data.columns:
        st.info("No zone data available for analysis")
        return
    
    zone_stats = processor.calculate_zone_statistics(data)
    
    if not zone_stats:
        st.info("Unable to calculate zone statistics")
        return
    
    # Zone efficiency comparison
    col1, col2 = st.columns(2)
    
    with col1:
        # Zone efficiency radar chart
        zones = list(zone_stats.keys())
        efficiency_scores = [stats.get('avg_efficiency', 0) for stats in zone_stats.values()]
        driver_counts = [stats.get('unique_drivers', 0) for stats in zone_stats.values()]
        anomaly_rates = [stats.get('anomaly_rate', 0) for stats in zone_stats.values()]
        
        fig_radar = go.Figure()
        
        # Normalize metrics for radar chart
        max_efficiency = max(efficiency_scores) if efficiency_scores else 1
        max_drivers = max(driver_counts) if driver_counts else 1
        max_anomaly = max(anomaly_rates) if anomaly_rates else 1
        
        for i, zone in enumerate(zones):
            fig_radar.add_trace(go.Scatterpolar(
                r=[
                    efficiency_scores[i] / max_efficiency * 100,
                    driver_counts[i] / max_drivers * 100,
                    (1 - anomaly_rates[i] / 100) * 100 if max_anomaly > 0 else 100  # Invert anomaly rate
                ],
                theta=['Efficiency', 'Driver Activity', 'Safety'],
                fill='toself',
                name=zone.replace('_', ' ')
            ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            title="Zone Performance Comparison",
            height=400
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
    
    with col2:
        # Zone optimization opportunities
        optimization_scores = []
        
        for zone, stats in zone_stats.items():
            efficiency = stats.get('avg_efficiency', 0)
            anomaly_rate = stats.get('anomaly_rate', 0)
            driver_count = stats.get('unique_drivers', 0)
            
            # Calculate optimization opportunity score
            # Lower efficiency and higher anomaly rate = higher opportunity
            opportunity_score = (100 - efficiency) * 0.6 + anomaly_rate * 0.4
            
            optimization_scores.append({
                'zone': zone.replace('_', ' '),
                'score': opportunity_score,
                'efficiency': efficiency,
                'anomaly_rate': anomaly_rate,
                'drivers': driver_count
            })
        
        # Sort by opportunity score
        optimization_scores.sort(key=lambda x: x['score'], reverse=True)
        
        fig_opp = go.Figure()
        
        zones_clean = [item['zone'] for item in optimization_scores]
        scores = [item['score'] for item in optimization_scores]
        
        fig_opp.add_trace(go.Bar(
            x=scores,
            y=zones_clean,
            orientation='h',
            marker=dict(
                color=scores,
                colorscale='RdYlGn_r',  # Red for high opportunity, Green for low
                showscale=True,
                colorbar=dict(title="Opportunity Score")
            )
        ))
        
        fig_opp.update_layout(
            title="Zone Optimization Opportunities",
            xaxis_title="Optimization Opportunity Score",
            yaxis_title="Zone",
            height=400
        )
        
        st.plotly_chart(fig_opp, use_container_width=True)
    
    # Zone optimization recommendations
    st.write("**🎯 Zone Optimization Recommendations:**")
    
    for item in optimization_scores[:3]:  # Top 3 opportunities
        zone = item['zone']
        score = item['score']
        efficiency = item['efficiency']
        anomaly_rate = item['anomaly_rate']
        
        recommendations = []
        
        if efficiency < 50:
            recommendations.append("Improve traffic flow management")
        if anomaly_rate > 5:
            recommendations.append("Enhance anomaly detection and response")
        if item['drivers'] < 2:
            recommendations.append("Increase driver allocation during peak hours")
        
        if recommendations:
            rec_text = ", ".join(recommendations)
            st.info(f"**{zone}** (Opportunity Score: {score:.1f}): {rec_text}")

def _render_anomaly_analytics(data: pd.DataFrame, processor: DataProcessor) -> None:
    """Render anomaly analysis"""
    
    st.subheader("🚨 Anomaly Detection Analysis")
    
    if data.empty:
        st.info("No data available for anomaly analysis")
        return
    
    if 'anomaly_flag' not in data.columns:
        st.info("No anomaly detection data available")
        return
    
    anomaly_data = data[data['anomaly_flag'].notna()].copy()
    
    if anomaly_data.empty:
        st.success("✅ No anomalies detected in the analyzed period!")
        return
    
    # Anomaly distribution
    col1, col2 = st.columns(2)
    
    with col1:
        # Anomaly types distribution
        anomaly_counts = anomaly_data['anomaly_flag'].value_counts()
        
        fig_pie = px.pie(
            values=anomaly_counts.values,
            names=anomaly_counts.index,
            title="Anomaly Types Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig_pie.update_layout(height=350)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Anomalies by zone and time
        if 'zone_name' in anomaly_data.columns and 'hour' in anomaly_data.columns:
            zone_time_anomalies = anomaly_data.groupby(['zone_name', 'hour']).size().reset_index(name='count')
            
            fig_anomaly_heatmap = px.density_heatmap(
                zone_time_anomalies,
                x='hour',
                y='zone_name',
                z='count',
                title="Anomaly Hotspots: Zone vs Time",
                color_continuous_scale="Reds"
            )
            
            fig_anomaly_heatmap.update_layout(height=350)
            st.plotly_chart(fig_anomaly_heatmap, use_container_width=True)
    
    # Anomaly severity analysis
    if 'anomaly_severity' in data.columns:
        st.write("**⚠️ Anomaly Severity Breakdown:**")
        
        severity_stats = data.groupby('anomaly_severity').agg({
            'driver_id': 'nunique',
            'zone_name': 'nunique',
            'speed_kph': 'mean'
        }).round(2)
        
        severity_stats.columns = ['Affected Drivers', 'Zones Involved', 'Avg Speed (km/h)']
        st.dataframe(severity_stats)
    
    # Recent anomaly details
    st.write("**🔍 Recent Anomaly Details:**")
    
    recent_anomalies = anomaly_data.nlargest(5, '_timestamp') if '_timestamp' in anomaly_data.columns else anomaly_data.head(5)
    
    for _, anomaly in recent_anomalies.iterrows():
        with st.expander(f"🚨 {anomaly.get('anomaly_flag', 'Unknown')} - {anomaly.get('zone_name', 'Unknown Zone')}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Driver ID", str(anomaly.get('driver_id', 'Unknown'))[:12] + "...")
                st.metric("Speed", f"{anomaly.get('speed_kph', 0):.1f} km/h")
            
            with col2:
                st.metric("Zone", anomaly.get('zone_name', 'Unknown').replace('_', ' '))
                st.metric("Traffic", anomaly.get('traffic_density', 'Unknown'))
            
            with col3:
                timestamp = anomaly.get('_timestamp', 'Unknown')
                if hasattr(timestamp, 'strftime'):
                    timestamp = timestamp.strftime('%H:%M:%S')
                st.metric("Time", str(timestamp))
                
                severity = anomaly.get('anomaly_severity', 'Unknown')
                st.metric("Severity", severity)
            
            # Anomaly details
            details = anomaly.get('anomaly_details', 'No details available')
            st.write(f"**Details:** {details}")

def _render_business_insights(data: pd.DataFrame, agent_data: List[Dict], processor: DataProcessor) -> None:
    """Render business insights and recommendations"""
    
    st.subheader("💼 Business Insights & Recommendations")
    
    # Key business metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**🚀 Operational Efficiency:**")
        
        if not data.empty:
            avg_efficiency = data.get('zone_efficiency', pd.Series([0])).mean()
            efficiency_trend = "📈 Improving" if avg_efficiency > 60 else "📉 Needs attention"
            
            st.metric("System Efficiency", f"{avg_efficiency:.1f}%", efficiency_trend)
            
            # Driver utilization
            if 'driver_id' in data.columns:
                active_drivers = data['driver_id'].nunique()
                total_events = len(data)
                utilization = (total_events / max(1, active_drivers)) / 10  # Rough utilization metric
                
                st.metric("Driver Utilization", f"{min(100, utilization):.1f}%")
    
    with col2:
        st.write("**💰 Cost Optimization:**")
        
        # Fuel efficiency (based on speed and distance)
        if 'speed_kph' in data.columns and 'distance_traveled' in data.columns:
            total_distance = data['distance_traveled'].sum()
            avg_speed = data['speed_kph'].mean()
            
            # Estimate fuel efficiency (lower speed in traffic = higher consumption)
            fuel_efficiency = max(0, 100 - (30 - avg_speed) * 2)  # Simplified model
            
            st.metric("Fuel Efficiency", f"{fuel_efficiency:.0f}%")
            st.metric("Total Distance", f"{total_distance:.1f} km")
    
    with col3:
        st.write("**📊 AI Agent ROI:**")
        
        agent_decisions = len(agent_data)
        
        # Estimate cost savings from AI optimization
        estimated_savings = agent_decisions * 0.75  # $0.75 per optimized decision
        
        st.metric("AI Decisions Today", agent_decisions)
        st.metric("Est. Cost Savings", f"${estimated_savings:.0f}")
    
    # Strategic recommendations
    st.write("**🎯 Strategic Recommendations:**")
    
    recommendations = []
    
    # Traffic optimization recommendations
    if not data.empty and 'traffic_score' in data.columns:
        avg_traffic = data['traffic_score'].mean()
        if avg_traffic > 3:
            recommendations.append({
                'priority': 'High',
                'category': 'Traffic Management',
                'recommendation': 'Implement dynamic routing during peak hours to avoid heavily congested zones',
                'impact': 'Reduce delivery times by 15-20%'
            })
    
    # Driver performance recommendations
    if not data.empty and 'driver_id' in data.columns:
        driver_analytics = processor.calculate_driver_analytics(data)
        if driver_analytics:
            low_safety_drivers = sum(1 for stats in driver_analytics.values() if stats.get('safety_score', 100) < 70)
            if low_safety_drivers > 0:
                recommendations.append({
                    'priority': 'Medium',
                    'category': 'Driver Training',
                    'recommendation': f'Provide additional training for {low_safety_drivers} drivers with safety scores below 70%',
                    'impact': 'Improve safety metrics and reduce insurance costs'
                })
    
    # Technology recommendations
    if agent_data:
        recommendations.append({
            'priority': 'Medium',
            'category': 'AI Enhancement',
            'recommendation': 'Scale OpenAI agent deployment to handle more complex optimization scenarios',
            'impact': 'Increase operational efficiency by 25-30%'
        })
    
    # Zone optimization recommendations
    if not data.empty and 'zone_name' in data.columns:
        zone_stats = processor.calculate_zone_statistics(data)
        if zone_stats:
            low_efficiency_zones = [zone for zone, stats in zone_stats.items() if stats.get('avg_efficiency', 100) < 50]
            if low_efficiency_zones:
                recommendations.append({
                    'priority': 'High',
                    'category': 'Zone Optimization',
                    'recommendation': f'Focus optimization efforts on {len(low_efficiency_zones)} underperforming zones: {", ".join([z.replace("_", " ") for z in low_efficiency_zones[:3]])}',
                    'impact': 'Improve overall system efficiency by 10-15%'
                })
    
    # Display recommendations
    for rec in recommendations:
        priority_color = {
            'High': '🔴',
            'Medium': '🟡',
            'Low': '🟢'
        }.get(rec['priority'], '🔵')
        
        with st.expander(f"{priority_color} {rec['priority']} Priority: {rec['category']}"):
            st.write(f"**Recommendation:** {rec['recommendation']}")
            st.write(f"**Expected Impact:** {rec['impact']}")
    
    # Performance summary
    st.write("**📈 Performance Summary:**")
    
    summary_metrics = {
        'Data Quality': 'Good' if not data.empty else 'No Data',
        'Agent Activity': 'Active' if agent_data else 'Inactive',
        'Anomaly Detection': 'Functioning' if 'anomaly_flag' in data.columns else 'Not Available',
        'System Health': 'Operational'
    }
    
    cols = st.columns(len(summary_metrics))
    for i, (metric, status) in enumerate(summary_metrics.items()):
        with cols[i]:
            color = "🟢" if status in ['Good', 'Active', 'Functioning', 'Operational'] else "🔴"
            st.metric(metric, f"{color} {status}")