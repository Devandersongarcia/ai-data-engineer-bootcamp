"""
Agent activity monitoring component
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List
import json

def render_agent_activity(agent_data: List[Dict], gps_data: pd.DataFrame, config: Dict) -> None:
    """Render agent activity monitoring interface"""
    
    st.header("🤖 Monitor de Atividade dos Agentes")
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Agent Monitor: Received {len(agent_data) if agent_data else 0} agent activities")
    
    if agent_data:
        logger.info("🔍 Agent Monitor: Sample activities:")
        for i, activity in enumerate(agent_data[:3]):
            logger.info(f"   Activity {i+1}: {activity.get('agent_type', 'Unknown')} - {activity.get('topic', 'unknown')}")
    
    # Show debug information on dashboard
    st.write(f"**Debug Info**: Received {len(agent_data) if agent_data else 0} agent activities")
    
    if not agent_data:
        st.warning("🤖 Nenhuma atividade de agente detectada. Inicie a demonstração dos agentes OpenAI para ver decisões de IA em tempo real!")
        st.write("**Solução de Problemas**: Verifique o botão 'Forçar Atualização' ou os logs para detalhes da recuperação de dados.")
        return
    
    # Agent activity controls
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        time_window = st.selectbox(
            "Janela de Atividade",
            options=[10, 30, 60, 120],
            index=1,
            format_func=lambda x: f"Últimos {x} minutos"
        )
    
    with col2:
        agent_filter = st.multiselect(
            "Filtrar Agentes",
            options=list(set(a.get('agent_type', 'Unknown') for a in agent_data)),
            default=list(set(a.get('agent_type', 'Unknown') for a in agent_data))[:4]
        )
    
    with col3:
        show_details = st.checkbox("Mostrar Detalhes das Decisões", value=True)
    
    # Filter agent data
    cutoff_time = datetime.now() - timedelta(minutes=time_window)
    filtered_activities = [
        a for a in agent_data 
        if a.get('timestamp', datetime.min) >= cutoff_time and 
           a.get('agent_type', 'Unknown') in agent_filter
    ]
    
    if not filtered_activities:
        st.info(f"Nenhuma atividade dos agentes nos últimos {time_window} minutos para os agentes selecionados.")
        return
    
    # Agent status overview
    _render_agent_status_overview(filtered_activities)
    
    st.divider()
    
    # Agent performance charts
    col1, col2 = st.columns(2)
    
    with col1:
        _render_agent_activity_chart(filtered_activities)
    
    with col2:
        _render_agent_response_times(filtered_activities)
    
    st.divider()
    
    # Recent decisions and live feed
    col1, col2 = st.columns([3, 2])
    
    with col1:
        if show_details:
            _render_agent_decisions_feed(filtered_activities)
    
    with col2:
        _render_agent_insights(filtered_activities, gps_data)

def _render_agent_status_overview(activities: List[Dict]) -> None:
    """Render agent status overview cards"""
    
    # Calculate agent statistics
    agent_stats = {}
    for activity in activities:
        agent_type = activity.get('agent_type', 'Unknown')
        if agent_type not in agent_stats:
            agent_stats[agent_type] = {
                'count': 0,
                'last_active': None,
                'avg_response_size': 0,
                'decisions': []
            }
        
        agent_stats[agent_type]['count'] += 1
        timestamp = activity.get('timestamp')
        
        if agent_stats[agent_type]['last_active'] is None or timestamp > agent_stats[agent_type]['last_active']:
            agent_stats[agent_type]['last_active'] = timestamp
        
        # Extract decision content
        data = activity.get('data', {})
        if isinstance(data, dict):
            decision = data.get('decision', data.get('recommendation', ''))
            if decision:
                agent_stats[agent_type]['decisions'].append(decision)
    
    # Display agent status cards
    st.subheader("🎯 Visão Geral do Status dos Agentes")
    
    if len(agent_stats) >= 4:
        cols = st.columns(4)
    else:
        cols = st.columns(len(agent_stats))
    
    agent_colors = {
        '⏱️ ETA Prediction': '#28a745',
        '🎯 Driver Allocation': '#17a2b8', 
        '🗺️ Route Optimization': '#ffc107',
        '🚨 System Alerts': '#dc3545'
    }
    
    for i, (agent_type, stats) in enumerate(agent_stats.items()):
        with cols[i % len(cols)]:
            # Status indicator
            last_active = stats['last_active']
            if last_active and (datetime.now() - last_active).total_seconds() < 300:  # 5 minutes
                status_color = "🟢"
                status_text = "Ativo"
            else:
                status_color = "🟡"
                status_text = "Inativo"
            
            # Agent card
            st.markdown(f"""
            <div style="
                background: {agent_colors.get(agent_type, '#6c757d')}; 
                color: white; 
                padding: 1rem; 
                border-radius: 8px; 
                margin: 0.5rem 0;
            ">
                <h4 style="margin: 0; font-size: 14px;">{agent_type}</h4>
                <p style="margin: 0.5rem 0; font-size: 12px;">{status_color} {status_text}</p>
                <p style="margin: 0; font-size: 18px; font-weight: bold;">{stats['count']} decisions</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Last active time
            if last_active:
                time_str = last_active.strftime("%H:%M:%S")
                st.caption(f"Last active: {time_str}")

def _render_agent_activity_chart(activities: List[Dict]) -> None:
    """Render agent activity timeline chart"""
    
    st.subheader("📊 Agent Activity Timeline")
    
    # Group activities by agent and time (5-minute buckets)
    agent_timeline = {}
    
    for activity in activities:
        agent_type = activity.get('agent_type', 'Unknown')
        timestamp = activity.get('timestamp')
        
        if not timestamp:
            continue
        
        # Create 5-minute bucket
        bucket = timestamp.replace(minute=(timestamp.minute // 5) * 5, second=0, microsecond=0)
        
        if agent_type not in agent_timeline:
            agent_timeline[agent_type] = {}
        
        agent_timeline[agent_type][bucket] = agent_timeline[agent_type].get(bucket, 0) + 1
    
    if not agent_timeline:
        st.info("No timeline data available")
        return
    
    # Create line chart
    fig = go.Figure()
    
    colors = ['#FF6B35', '#F7931E', '#4ECDC4', '#45B7D1', '#96CEB4']
    
    for i, (agent_type, timeline) in enumerate(agent_timeline.items()):
        x_vals = sorted(timeline.keys())
        y_vals = [timeline[x] for x in x_vals]
        
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='lines+markers',
            name=agent_type,
            line=dict(color=colors[i % len(colors)], width=3),
            marker=dict(size=6),
            hovertemplate="<b>%{fullData.name}</b><br>" +
                          "Time: %{x}<br>" +
                          "Decisions: %{y}<br>" +
                          "<extra></extra>"
        ))
    
    fig.update_layout(
        title="Decisões dos Agentes ao Longo do Tempo (intervalos de 5 min)",
        xaxis_title="Tempo",
        yaxis_title="Número de Decisões",
        height=350,
        margin=dict(t=40, b=20, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    
    st.plotly_chart(fig, use_container_width=True)

def _render_agent_response_times(activities: List[Dict]) -> None:
    """Render agent response time analysis"""
    
    st.subheader("⚡ Performance dos Agentes")
    
    # Calculate response metrics (simulated based on decision complexity)
    agent_metrics = {}
    
    for activity in activities:
        agent_type = activity.get('agent_type', 'Unknown')
        data = activity.get('data', {})
        
        if agent_type not in agent_metrics:
            agent_metrics[agent_type] = {
                'response_times': [],
                'decision_sizes': [],
                'success_rate': 100
            }
        
        # Simulate response time based on decision complexity
        decision_text = str(data.get('decision', data.get('recommendation', '')))
        response_time = min(2.0, max(0.1, len(decision_text) * 0.01))  # 0.1 to 2.0 seconds
        
        agent_metrics[agent_type]['response_times'].append(response_time)
        agent_metrics[agent_type]['decision_sizes'].append(len(decision_text))
    
    # Create performance chart
    agent_names = []
    avg_response_times = []
    decision_counts = []
    
    for agent_type, metrics in agent_metrics.items():
        agent_names.append(agent_type.replace('⏱️ ', '').replace('🎯 ', '').replace('🗺️ ', '').replace('🚨 ', ''))
        avg_response_times.append(sum(metrics['response_times']) / len(metrics['response_times']) if metrics['response_times'] else 0)
        decision_counts.append(len(metrics['response_times']))
    
    # Create bubble chart for performance
    fig_perf = go.Figure()
    
    fig_perf.add_trace(go.Scatter(
        x=agent_names,
        y=avg_response_times,
        mode='markers',
        marker=dict(
            size=[max(20, count * 3) for count in decision_counts],
            color=avg_response_times,
            colorscale='RdYlGn_r',  # Red for slow, Green for fast
            showscale=True,
            colorbar=dict(title="Tempo Médio de Resposta (s)"),
            opacity=0.7
        ),
        hovertemplate="<b>%{x}</b><br>" +
                      "Resposta Média: %{y:.2f}s<br>" +
                      "Decisões: %{text}<br>" +
                      "<extra></extra>",
        text=decision_counts
    ))
    
    fig_perf.update_layout(
        title="Performance dos Agentes: Tempo de Resposta vs Atividade",
        xaxis_title="Tipo de Agente",
        yaxis_title="Tempo Médio de Resposta (segundos)",
        height=350,
        margin=dict(t=40, b=20, l=20, r=20),
        showlegend=False
    )
    
    st.plotly_chart(fig_perf, use_container_width=True)

def _render_agent_decisions_feed(activities: List[Dict]) -> None:
    """Render live agent decisions feed"""
    
    st.subheader("📝 Decisões Recentes dos Agentes")
    
    # Sort activities by timestamp (most recent first)
    sorted_activities = sorted(
        activities, 
        key=lambda x: x.get('timestamp', datetime.min), 
        reverse=True
    )
    
    # Display recent decisions (increased from 10 to 100)
    for i, activity in enumerate(sorted_activities[:100]):  # Show last 100 decisions
        agent_type = activity.get('agent_type', 'Unknown')
        timestamp = activity.get('timestamp')
        data = activity.get('data', {})
        
        # Format timestamp
        time_str = timestamp.strftime("%H:%M:%S") if timestamp else "Desconhecido"
        
        # Extract decision content based on agent type
        decision = None
        if 'Route Optimization' in agent_type:
            decision = data.get('optimization', 'Nenhuma otimização de rota')
        elif 'ETA Prediction' in agent_type:
            decision = data.get('prediction', 'Nenhuma predição de ETA')
        elif 'Driver Allocation' in agent_type:
            decision = data.get('allocation', 'Nenhuma decisão de alocação')
        elif 'System Alerts' in agent_type:
            alert_type = data.get('type', 'Desconhecido')
            alert_details = data.get('details', 'Sem detalhes')
            decision = f"Alerta: {alert_type} - {alert_details}"
        else:
            decision = data.get('decision', data.get('recommendation', data.get('analysis', 'Sem dados de decisão')))
        
        # Get additional context based on agent type
        context = {}
        if 'Route Optimization' in agent_type:
            for key in ['driver_id', 'zone', 'priority', 'estimated_time_savings']:
                if key in data:
                    context[key] = data[key]
        elif 'ETA Prediction' in agent_type:
            for key in ['driver_id', 'zone', 'confidence', 'factors']:
                if key in data:
                    if key == 'factors' and isinstance(data[key], dict):
                        context['traffic'] = data[key].get('traffic_density', 'Unknown')
                        context['speed'] = data[key].get('current_speed', 'Unknown')
                    else:
                        context[key] = data[key]
        elif 'System Alerts' in agent_type:
            for key in ['driver_id', 'zone', 'severity', 'type']:
                if key in data:
                    context[key] = data[key]
        else:
            # Default context for other agent types
            for key in ['driver_id', 'zone', 'speed', 'traffic_density', 'anomaly_flag']:
                if key in data:
                    context[key] = data[key]
        
        # Display decision card
        with st.expander(f"[{time_str}] Decisão do {agent_type}", expanded=(i < 3)):
            
            # Debug: Show raw data structure for first few items
            if i < 2:  # Show debug for first 2 items
                st.write("**Debug - Raw Data:**")
                st.json(data)
            
            # Context information
            if context:
                st.write("**Contexto:**")
                context_cols = st.columns(len(context))
                for j, (key, value) in enumerate(context.items()):
                    with context_cols[j]:
                        st.metric(key.replace('_', ' ').title(), str(value)[:20])
            
            # Decision content
            st.write("**Decisão/Recomendação:**")
            
            # Clean and format decision text
            if isinstance(decision, dict):
                decision_text = json.dumps(decision, indent=2)
            else:
                decision_text = str(decision)
            
            # Highlight key parts of the decision
            if any(keyword in decision_text.lower() for keyword in ['recommendation', 'suggest', 'should', 'optimize']):
                st.success(decision_text)
            elif any(keyword in decision_text.lower() for keyword in ['alert', 'warning', 'anomaly', 'problem']):
                st.error(decision_text)
            else:
                st.info(decision_text)
            
            # Show raw data if available
            if st.checkbox(f"Show raw data {i}", key=f"raw_data_{i}"):
                st.json(data)

def _render_agent_insights(activities: List[Dict], gps_data: pd.DataFrame) -> None:
    """Render agent insights and analytics"""
    
    st.subheader("🧠 Agent Insights")
    
    # Decision categories analysis
    decision_categories = {
        'Optimization': 0,
        'Alerts': 0,
        'Predictions': 0,
        'Allocations': 0
    }
    
    for activity in activities:
        agent_type = activity.get('agent_type', '')
        if 'Route Optimization' in agent_type:
            decision_categories['Optimization'] += 1
        elif 'System Alerts' in agent_type:
            decision_categories['Alerts'] += 1
        elif 'ETA Prediction' in agent_type:
            decision_categories['Predictions'] += 1
        elif 'Driver Allocation' in agent_type:
            decision_categories['Allocations'] += 1
    
    # Decision types pie chart
    if sum(decision_categories.values()) > 0:
        fig_pie = px.pie(
            values=list(decision_categories.values()),
            names=list(decision_categories.keys()),
            title="Decision Types Distribution",
            color_discrete_sequence=['#FF6B35', '#F7931E', '#4ECDC4', '#45B7D1']
        )
        
        fig_pie.update_layout(
            height=300,
            margin=dict(t=40, b=20, l=20, r=20),
            showlegend=True
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Agent effectiveness metrics
    st.write("**📊 Agent Effectiveness:**")
    
    total_decisions = len(activities)
    unique_situations = len(set(str(a.get('data', {})) for a in activities))
    
    effectiveness_score = min(100, (unique_situations / max(1, total_decisions)) * 100 + 50)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Decisions", total_decisions)
        st.metric("Unique Situations", unique_situations)
    
    with col2:
        st.metric("Effectiveness Score", f"{effectiveness_score:.0f}%")
        st.metric("Avg Decision/Min", f"{total_decisions / max(1, len(activities) / 10):.1f}")
    
    # Top agent insights
    st.write("**🎯 Key Insights:**")
    
    insights = []
    
    # Analyze decision patterns
    agent_activity_count = {}
    for activity in activities:
        agent_type = activity.get('agent_type', 'Unknown')
        agent_activity_count[agent_type] = agent_activity_count.get(agent_type, 0) + 1
    
    if agent_activity_count:
        most_active_agent = max(agent_activity_count.items(), key=lambda x: x[1])
        insights.append(f"🏆 {most_active_agent[0]} is most active with {most_active_agent[1]} decisions")
    
    # GPS data insights
    if not gps_data.empty:
        if 'anomaly_flag' in gps_data.columns:
            anomaly_count = gps_data['anomaly_flag'].notna().sum()
            if anomaly_count > 0:
                insights.append(f"⚠️ {anomaly_count} anomalies detected and processed by agents")
        
        if 'speed_kph' in gps_data.columns:
            avg_speed = gps_data['speed_kph'].mean()
            if avg_speed < 15:
                insights.append(f"🚗 Heavy traffic detected (avg {avg_speed:.1f} km/h) - Route agents active")
            elif avg_speed > 40:
                insights.append(f"⚡ High speed conditions (avg {avg_speed:.1f} km/h) - ETA agents optimizing")
    
    # Recent activity insight
    if activities:
        latest_activity = max(activities, key=lambda x: x.get('timestamp', datetime.min))
        time_since_last = (datetime.now() - latest_activity.get('timestamp', datetime.now())).total_seconds()
        
        if time_since_last < 60:
            insights.append(f"🔄 Agents are actively processing (last decision {int(time_since_last)}s ago)")
        elif time_since_last < 300:
            insights.append(f"⏸️ Agents are idle (last decision {int(time_since_last/60)}m ago)")
    
    # Display insights
    if insights:
        for insight in insights[:5]:  # Show top 5 insights
            st.info(insight)
    else:
        st.info("💡 Collect more agent activity data to see insights")
    
    # Agent health status
    st.write("**🏥 Agent Health:**")
    
    health_status = "🟢 All agents healthy"
    if total_decisions == 0:
        health_status = "🔴 No agent activity"
    elif total_decisions < 5:
        health_status = "🟡 Low agent activity"
    
    st.write(health_status)