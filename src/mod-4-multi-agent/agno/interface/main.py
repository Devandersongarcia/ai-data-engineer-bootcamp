#!/usr/bin/env python3
"""
🚚 UberEats Delivery Optimization Dashboard
Real-time analytics, GPS tracking, and agent monitoring

Run with: streamlit run interface/main.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import json
import os
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dashboard.log')
    ]
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from interface.config.settings import DashboardConfig
from interface.utils.kafka_consumer import KafkaDataStream
from interface.utils.data_processor import DataProcessor
from interface.components.sidebar import render_sidebar
from interface.components.metrics import render_metrics_dashboard
from interface.components.map_view import render_gps_map
from interface.components.agent_monitor import render_agent_activity
from interface.components.analytics import render_analytics_charts

# Configure Streamlit page
st.set_page_config(
    page_title="🚚 UberEats Dashboard de Otimização",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #FF6B35, #F7931E);
        padding: 1rem 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #FF6B35;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .status-online {
        color: #28a745;
        font-weight: bold;
    }
    
    .status-offline {
        color: #dc3545;
        font-weight: bold;
    }
    
    .agent-active {
        background: linear-gradient(90deg, #28a745, #20c997);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
    }
    
    .zone-high-activity {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 0.5rem;
        margin: 0.25rem 0;
    }
</style>
""", unsafe_allow_html=True)

class UberEatsDashboard:
    """Main dashboard application"""
    
    def __init__(self):
        logger.info("🚀 Initializing UberEats Dashboard")
        self.config = DashboardConfig()
        self.data_processor = DataProcessor()
        
        logger.info(f"📋 Dashboard config loaded - Agent topics: {self.config.agent_topics}")
        
        # Initialize session state safely
        self._init_session_state()
        logger.info("✅ Dashboard initialization complete")
    
    def _init_session_state(self):
        """Safely initialize session state"""
        if not hasattr(st, 'session_state'):
            # Create mock session state for testing
            self.session_state = {
                'kafka_stream': None,
                'last_update': datetime.now(),
                'gps_data': pd.DataFrame(),
                'agent_data': []
            }
        else:
            self.session_state = st.session_state
            if 'kafka_stream' not in st.session_state:
                st.session_state.kafka_stream = None
            if 'last_update' not in st.session_state:
                st.session_state.last_update = datetime.now()
            if 'gps_data' not in st.session_state:
                st.session_state.gps_data = pd.DataFrame()
            if 'agent_data' not in st.session_state:
                st.session_state.agent_data = []
    
    def render_header(self):
        """Render main dashboard header"""
        st.markdown("""
        <div class="main-header">
            <h1>🚚 UberEats Dashboard de Otimização de Entregas</h1>
            <p>Rastreamento GPS em tempo real • Otimização com IA • Operações São Paulo</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_connection_status(self):
        """Display Kafka connection status"""
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if self.session_state.get('kafka_stream') and self.session_state['kafka_stream'].is_connected():
                st.markdown("**Status:** <span class='status-online'>🟢 Conectado ao Kafka</span>", 
                          unsafe_allow_html=True)
            else:
                st.markdown("**Status:** <span class='status-offline'>🔴 Desconectado</span>", 
                          unsafe_allow_html=True)
        
        with col2:
            st.metric("Última Atualização", 
                     self.session_state.get('last_update', datetime.now()).strftime("%H:%M:%S"))
        
        with col3:
            if st.button("🔄 Atualizar Dados"):
                self.refresh_data()
    
    def refresh_data(self):
        """Refresh dashboard data"""
        try:
            logger.info("🔄 Starting data refresh...")
            
            # Initialize Kafka stream if not exists
            if not self.session_state.get('kafka_stream'):
                logger.info("🔄 Initializing Kafka stream...")
                self.session_state['kafka_stream'] = KafkaDataStream()
                logger.info(f"✅ Kafka stream created, connected: {self.session_state['kafka_stream'].is_connected()}")
            
            # Fetch latest GPS data
            logger.info("📍 Fetching GPS data...")
            new_gps_data = self.session_state['kafka_stream'].get_recent_gps_data()
            logger.info(f"📍 GPS data fetched: {len(new_gps_data)} records")
            if not new_gps_data.empty:
                self.session_state['gps_data'] = new_gps_data
                logger.info(f"📍 GPS data updated with {len(new_gps_data)} records")
            
            # Fetch agent activity
            logger.info("🤖 Fetching agent activity...")
            agent_data = self.session_state['kafka_stream'].get_agent_activity()
            logger.info(f"🤖 Agent activity fetched: {len(agent_data)} activities")
            
            if agent_data:
                logger.info("🤖 Agent activities details:")
                for i, activity in enumerate(agent_data[:3]):  # Log first 3
                    logger.info(f"   Activity {i+1}: {activity.get('agent_type')} - {activity.get('timestamp')} - Topic: {activity.get('topic')}")
            
            self.session_state['agent_data'] = agent_data
            
            self.session_state['last_update'] = datetime.now()
            logger.info(f"✅ Data refresh complete at {self.session_state['last_update']}")
            
            # Show success message only if we have Streamlit context
            if hasattr(st, 'success') and len(agent_data) > 0:
                st.success(f"📡 Dados atualizados! Encontradas {len(agent_data)} atividades dos agentes")
                logger.info(f"✅ Showing success message with {len(agent_data)} activities")
            elif hasattr(st, 'info'):
                st.info("📡 Dados atualizados - aguardando atividade dos agentes")
                logger.warning("⚠️ No agent activities found")
            
        except Exception as e:
            logger.error(f"❌ Error refreshing data: {str(e)}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            if hasattr(st, 'error'):
                st.error(f"❌ Erro ao atualizar dados: {str(e)}")
    
    def run(self):
        """Main dashboard application"""
        logger.info("🎯 Running main dashboard application")
        
        # Header
        self.render_header()
        
        # Initialize data on first load
        if not self.session_state.get('kafka_stream'):
            logger.info("🔄 First load - initializing Kafka connection")
            with st.spinner("🔄 Conectando ao Kafka e carregando dados..."):
                self.refresh_data()
        
        # Connection status
        self.render_connection_status()
        
        # Enhanced data loading status with logging
        st.write("### 📊 Status do Sistema")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            gps_count = len(self.session_state.get('gps_data', pd.DataFrame()))
            st.metric("Eventos GPS", gps_count)
            
        with col2:
            agent_count = len(self.session_state.get('agent_data', []))
            delta = f"+{agent_count}" if agent_count > 0 else None
            st.metric("Atividades dos Agentes", agent_count, delta=delta)
            
        with col3:
            kafka_status = "Conectado" if self.session_state.get('kafka_stream') and self.session_state['kafka_stream'].is_connected() else "Desconectado"
            st.metric("Status Kafka", kafka_status)
            
        with col4:
            last_update = self.session_state.get('last_update')
            if last_update:
                time_ago = (datetime.now() - last_update).total_seconds()
                if time_ago < 60:
                    update_str = f"{int(time_ago)}s ago"
                else:
                    update_str = f"{int(time_ago/60)}m ago"
                st.metric("Última Atualização", update_str)
            else:
                st.metric("Última Atualização", "Nunca")
        
        # Enhanced refresh controls
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            if st.button("🔄 Forçar Atualização", help="Atualizar manualmente com logging detalhado"):
                logger.info("🔄 MANUAL REFRESH triggered by user")
                with st.spinner("🔍 Buscando dados atualizados com polling otimizado..."):
                    self.refresh_data()
                st.rerun()
                
        with col2:
            auto_refresh = st.checkbox("🔄 Atualização Automática", value=True, help="Atualizar automaticamente a cada 30 segundos")
            
        with col3:
            if st.button("📋 Mostrar Logs Recentes", help="Exibir logs recentes do dashboard"):
                try:
                    with open('dashboard.log', 'r') as f:
                        logs = f.readlines()[-20:]  # Last 20 lines
                        st.text_area("Logs Recentes", "".join(logs), height=200)
                except Exception as e:
                    st.error(f"Não foi possível ler os logs: {e}")
        
        # Status indicators
        if self.session_state.get('agent_data'):
            st.success(f"✅ Ativo: Encontradas {len(self.session_state['agent_data'])} atividades dos agentes")
            logger.info(f"✅ UI Status: Showing {len(self.session_state['agent_data'])} activities")
        else:
            st.info("⏳ Aguardando atividade dos agentes - ingestão de dados em andamento...")
            logger.info("⏳ UI Status: No activities to display")
        
        # Sidebar controls
        sidebar_config = render_sidebar()
        
        # Auto-refresh logic
        if sidebar_config.get('auto_refresh', True):
            refresh_interval = sidebar_config.get('refresh_interval', 30)
            last_update = self.session_state.get('last_update', datetime.now())
            if (datetime.now() - last_update).seconds >= refresh_interval:
                self.refresh_data()
        
        # Main dashboard tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Métricas em Tempo Real", 
            "🗺️ Rastreamento GPS", 
            "🤖 Atividade dos Agentes", 
            "📈 Análises"
        ])
        
        with tab1:
            render_metrics_dashboard(
                gps_data=self.session_state.get('gps_data', pd.DataFrame()),
                agent_data=self.session_state.get('agent_data', []),
                config=sidebar_config
            )
        
        with tab2:
            render_gps_map(
                gps_data=self.session_state.get('gps_data', pd.DataFrame()),
                config=sidebar_config
            )
        
        with tab3:
            # Debug agent data before passing to component
            agent_data_debug = self.session_state.get('agent_data', [])
            logger.info(f"🔍 Main Dashboard: Passing {len(agent_data_debug)} agent activities to Agent Activity tab")
            if agent_data_debug:
                logger.info(f"🔍 Main Dashboard: First activity: {agent_data_debug[0].get('agent_type', 'Unknown')} from {agent_data_debug[0].get('topic', 'unknown')}")
            
            render_agent_activity(
                agent_data=agent_data_debug,
                gps_data=self.session_state.get('gps_data', pd.DataFrame()),
                config=sidebar_config
            )
        
        with tab4:
            render_analytics_charts(
                gps_data=self.session_state.get('gps_data', pd.DataFrame()),
                agent_data=self.session_state.get('agent_data', []),
                config=sidebar_config
            )

def main():
    """Entry point for Streamlit dashboard"""
    dashboard = UberEatsDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()