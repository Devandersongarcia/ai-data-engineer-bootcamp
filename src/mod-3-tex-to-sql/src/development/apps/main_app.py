"""Production-ready Streamlit application for text-to-SQL conversion.

This application provides a comprehensive interface for natural language
to SQL conversion with advanced monitoring, error handling, and user experience features.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Configure Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_dev_settings
from core.text_to_sql import TextToSQLConverter
from utils.logging_utils import setup_logging, get_logger

# Initialize application environment
load_dotenv()
settings = get_dev_settings()
setup_logging(settings)
logger = get_logger(__name__)


def configure_page():
    """Configure Streamlit page settings and layout."""
    st.set_page_config(
        page_title=settings.app_title,
        page_icon=settings.app_icon,
        layout=settings.app_layout,
        initial_sidebar_state="expanded"
    )


def render_header():
    """Render application header with branding."""
    st.title(f"{settings.app_icon} UberEats Brasil")
    st.subheader("Sistema de Consulta Inteligente de Notas Fiscais")
    
    with st.expander("ℹ️ Sobre o Sistema", expanded=False):
        st.markdown("""
        **Sistema de Text-to-SQL com IA**
        
        - 🤖 Conversão automática de linguagem natural para SQL
        - 🔒 Validação de segurança para consultas
        - 📊 Análise de dados em tempo real
        - 📈 Monitoramento de performance e custos
        
        **Como usar:**
        1. Configure sua chave da API OpenAI
        2. Digite sua pergunta em português
        3. Visualize os resultados automaticamente
        """)


def render_configuration_panel():
    """Render configuration panel with API settings."""
    with st.expander("⚙️ Configuração do Sistema", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔑 Credenciais")
            openai_api_key = st.text_input(
                "Chave OpenAI API",
                value=settings.openai_api_key or "",
                type="password",
                help="Insira sua chave da API OpenAI para habilitar o processamento"
            )
            
        with col2:
            st.subheader("🗄️ Banco de Dados")
            database_url = st.text_input(
                "URL do Banco de Dados",
                value=settings.database_url,
                disabled=True,
                help="Conexão com o banco PostgreSQL (configurado automaticamente)"
            )
            
            # Model configuration
            model_name = st.selectbox(
                "Modelo OpenAI",
                options=["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo-preview"],
                index=0 if settings.openai_model == "gpt-4" else 1,
                help="Selecione o modelo de IA para processamento"
            )
    
    return openai_api_key, database_url, model_name


def initialize_converter(openai_api_key: str, model_name: str):
    """Initialize the text-to-SQL converter with error handling."""
    if 'converter' not in st.session_state or st.session_state.get('current_model') != model_name:
        try:
            with st.spinner("🔧 Inicializando sistema..."):
                logger.info("Initializing TextToSQLConverter")
                
                # Update settings
                current_settings = settings
                current_settings.openai_api_key = openai_api_key
                current_settings.openai_model = model_name
                
                st.session_state.converter = TextToSQLConverter(
                    settings=current_settings,
                    openai_api_key=openai_api_key
                )
                st.session_state.current_model = model_name
                
                logger.info("TextToSQLConverter initialized successfully")
                st.success("✅ Sistema inicializado com sucesso!")
                
        except Exception as e:
            logger.error(f"Converter initialization failed: {e}")
            st.error(f"❌ Erro na inicialização: {str(e)}")
            st.info("💡 Verifique sua chave da API OpenAI e tente novamente.")
            return False
    
    return True


def render_query_interface():
    """Render the main query interface with advanced features."""
    st.markdown("---")
    st.subheader("💬 Consulta de Dados")
    
    # Query input with enhanced features
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_question = st.text_area(
            "Digite sua pergunta em português:",
            placeholder="Ex: Mostre o faturamento dos últimos 30 dias por restaurante",
            height=100,
            help="Descreva o que você gostaria de consultar em linguagem natural"
        )
    
    with col2:
        st.markdown("**💡 Exemplos:**")
        example_questions = [
            "Top 10 restaurantes",
            "Faturamento mensal", 
            "Notas fiscais recentes",
            "Análise de pagamentos",
            "Pedidos por região"
        ]
        
        for example in example_questions:
            if st.button(example, key=f"example_{example}", use_container_width=True):
                st.session_state.example_question = example
    
    # Use example question if selected
    if 'example_question' in st.session_state:
        user_question = st.session_state.example_question
        st.session_state.pop('example_question', None)
        st.rerun()
    
    return user_question


def process_query(user_question: str):
    """Process user query with comprehensive error handling and metrics."""
    if not user_question.strip():
        st.warning("⚠️ Digite uma pergunta para consultar os dados.")
        return
    
    logger.info(f"Processing question: {user_question[:100]}...")
    
    # Create progress tracking
    progress_container = st.container()
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🔄 Processando pergunta...")
            progress_bar.progress(25)
            
            start_time = datetime.now()
            result = st.session_state.converter.process_question(user_question)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            progress_bar.progress(100)
            status_text.text("✅ Processamento concluído!")
            
            # Clear progress after brief delay
            import time
            time.sleep(1)
            progress_container.empty()
            
            logger.info(f"Question processed in {processing_time:.2f} seconds")
            return result, processing_time
            
        except Exception as e:
            progress_container.empty()
            logger.error(f"Query processing failed: {e}")
            st.error(f"❌ Erro no processamento: {str(e)}")
            return None, 0


def render_data_visualization(df):
    """Render data visualizations based on DataFrame content."""
    if df.empty:
        st.info("Nenhum dado disponível para visualização.")
        return
    
    # Auto-detect visualization opportunities
    numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
    categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    if len(numeric_columns) > 0:
        st.subheader("📊 Estatísticas Descritivas")
        st.dataframe(df[numeric_columns].describe())
        
        if len(categorical_columns) > 0 and len(numeric_columns) > 0:
            st.subheader("📈 Gráficos")
            
            # Simple bar chart
            if len(categorical_columns) >= 1 and len(numeric_columns) >= 1:
                try:
                    chart_data = df.groupby(categorical_columns[0])[numeric_columns[0]].sum().head(10)
                    st.bar_chart(chart_data)
                except Exception as e:
                    st.warning(f"Não foi possível gerar gráfico: {e}")
    else:
        st.info("📊 Dados não numéricos - visualização limitada.")
        st.write(f"**Colunas disponíveis:** {', '.join(df.columns.tolist())}")


def display_results(result: dict, processing_time: float):
    """Display query results with comprehensive metrics and visualizations."""
    if result["success"]:
        records_found = len(result['result']) if result['result'] is not None else 0
        logger.info(f"Query executed successfully. Records found: {records_found}")
        
        # Success metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Status", "Sucesso", delta="✅")
        with col2:
            st.metric("📝 Registros", records_found)
        with col3:
            st.metric("⏱️ Tempo", f"{processing_time:.2f}s")
        with col4:
            if result.get("estimated_cost"):
                st.metric("💰 Custo", f"${result['estimated_cost']:.6f}")
        
        if result["result"] is not None and not result["result"].empty:
            # Data visualization options
            display_tab1, display_tab2, display_tab3 = st.tabs(["📊 Dados", "📈 Visualização", "🔍 SQL"])
            
            with display_tab1:
                st.dataframe(
                    result["result"],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Download options
                col1, col2 = st.columns(2)
                with col1:
                    csv = result["result"].to_csv(index=False)
                    st.download_button(
                        "📥 Baixar CSV",
                        data=csv,
                        file_name=f"consulta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                with col2:
                    json_data = result["result"].to_json(orient="records", indent=2)
                    st.download_button(
                        "📄 Baixar JSON",
                        data=json_data,
                        file_name=f"consulta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            
            with display_tab2:
                render_data_visualization(result["result"])
            
            with display_tab3:
                st.code(result["sql_query"], language="sql")
                
                # SQL metrics
                if result.get("token_usage"):
                    st.json(result["token_usage"])
        else:
            st.info("🔍 Consulta executada com sucesso, mas nenhum resultado encontrado.")
            with st.expander("🔍 Ver consulta SQL gerada"):
                st.code(result["sql_query"], language="sql")


def display_error(result: dict):
    """Display error information with diagnostic details."""
    st.error(f"❌ **Erro:** {result['error']}")
    logger.error(f"Error processing query: {result['error']}")
    
    # Error details in expander
    with st.expander("🔧 Detalhes do Erro"):
        if result.get("sql_query"):
            st.subheader("SQL Gerada:")
            st.code(result["sql_query"], language="sql")
        
        if result.get("error_id"):
            st.text(f"ID do Erro: {result['error_id']}")
        
        # Troubleshooting suggestions
        st.subheader("💡 Sugestões:")
        suggestions = [
            "Tente reformular a pergunta de forma mais específica",
            "Verifique se os nomes de campos estão corretos",
            "Simplifique a consulta dividindo em partes menores",
            "Consulte os exemplos disponíveis na interface"
        ]
        for suggestion in suggestions:
            st.write(f"• {suggestion}")


def render_sidebar():
    """Render sidebar with system status and metrics."""
    with st.sidebar:
        st.header("📊 Status do Sistema")
        
        # System health indicators
        if 'converter' in st.session_state:
            st.success("✅ Sistema Online")
            st.info(f"🤖 Modelo: {st.session_state.get('current_model', 'N/A')}")
        else:
            st.warning("⚠️ Sistema Offline")
        
        st.markdown("---")
        
        # Query history (if available)
        if 'query_history' not in st.session_state:
            st.session_state.query_history = []
        
        st.header("📝 Histórico de Consultas")
        if st.session_state.query_history:
            for i, query in enumerate(st.session_state.query_history[-5:], 1):
                with st.expander(f"Consulta {i}"):
                    st.write(query.get('question', 'N/A')[:100] + '...')
                    st.write(f"Status: {query.get('status', 'N/A')}")
                    st.write(f"Registros: {query.get('records', 0)}")
        else:
            st.info("Nenhuma consulta realizada ainda.")
        
        if st.button("🗑️ Limpar Histórico"):
            st.session_state.query_history = []
            st.rerun()


def main():
    """Main application entry point with comprehensive error handling."""
    configure_page()
    render_header()
    render_sidebar()
    
    # Configuration panel
    openai_api_key, database_url, model_name = render_configuration_panel()
    
    if not openai_api_key:
        st.warning("⚠️ **Configure sua chave da API OpenAI** para começar.")
        
        with st.expander("ℹ️ Como obter uma chave da API OpenAI", expanded=True):
            st.markdown("""
            1. Acesse [platform.openai.com](https://platform.openai.com)
            2. Faça login ou crie uma conta
            3. Vá para a seção "API Keys"
            4. Clique em "Create new secret key"
            5. Copie a chave e cole na configuração acima
            """)
        return
    
    # Initialize converter
    if not initialize_converter(openai_api_key, model_name):
        return
    
    # Main query interface
    user_question = render_query_interface()
    
    # Process query button
    if st.button("🔍 **Processar Consulta**", type="primary", use_container_width=True):
        query_result = process_query(user_question)
        
        if query_result:
            result, processing_time = query_result
            
            # Add to history
            history_entry = {
                'question': user_question,
                'status': 'Sucesso' if result['success'] else 'Erro',
                'records': len(result['result']) if result.get('result') is not None else 0,
                'timestamp': datetime.now().isoformat()
            }
            st.session_state.query_history.append(history_entry)
            
            if result["success"]:
                display_results(result, processing_time)
            else:
                display_error(result)
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🍔 **UberEats Brasil**")
    with col2:
        st.markdown("⚡ **Powered by OpenAI**")
    with col3:
        st.markdown(f"📅 **{datetime.now().strftime('%Y-%m-%d')}**")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Erro crítico na aplicação: {str(e)}")
        logger.critical(f"Critical application error: {e}")