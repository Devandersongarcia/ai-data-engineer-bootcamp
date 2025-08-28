# IMPORTANT: Set environment variables BEFORE any other imports
import os
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
os.environ['TOKENIZERS_PARALLELISM'] = 'false' 
os.environ['POSTHOG_DISABLE'] = 'true'
os.environ['CHROMA_TELEMETRY'] = 'False'

import streamlit as st
import logging
import sys
import os
from datetime import datetime

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vanna_converter import VannaTextToSQLConverter
from config.settings import get_settings
from dotenv import load_dotenv
import hashlib
import shutil

load_dotenv()

# Get application settings
settings = get_settings()

# Configure logging using settings
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure Streamlit page using settings
st.set_page_config(
    page_title=f"{settings.app_title} - Consulta com Vanna.ai",
    page_icon=settings.app_icon,
    layout=settings.app_layout
)

# Header with Vanna.ai branding using settings
st.title(f"{settings.app_icon} {settings.app_title}")
st.subheader("Consulta Inteligente com Vanna.ai")
st.caption("🤖 Powered by Vanna.ai - AI SQL Agent")

# Simplified configuration in main area
with st.expander("⚙️ Configuração", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        openai_api_key = st.text_input(
            "Chave OpenAI API",
            value=settings.openai_api_key or "",
            type="password"
        )
    with col2:
        database_url = st.text_input(
            "URL do Banco",
            value=settings.database_url,
            disabled=True
        )

# Initialize the Vanna converter with better caching
if openai_api_key and database_url:
    # Create a hash of the configuration to detect changes
    config_hash = hashlib.md5(f"{openai_api_key[:10]}{database_url}".encode()).hexdigest()
    
    try:
        # Use @st.cache_resource for better Streamlit caching
        @st.cache_resource(show_spinner=False)
        def get_vanna_converter(_database_url, _openai_api_key, _config_hash):
            """Cached Vanna converter initialization"""
            return VannaTextToSQLConverter(
                database_url=_database_url,
                openai_api_key=_openai_api_key
            )
        
        # Check if we need to reinitialize (config changed or not initialized)
        if ('vanna_converter' not in st.session_state or 
            st.session_state.get('vanna_config_hash') != config_hash):
            
            logger.info("Inicializando VannaTextToSQLConverter")
            
            # Show initialization progress
            init_placeholder = st.empty()
            progress_bar = st.progress(0)
            
            with init_placeholder.container():
                st.info("🤖 Inicializando Vanna.ai...")
                st.caption("Esta operação pode levar alguns segundos na primeira execução")
            
            progress_bar.progress(25)
            
            try:
                # Use cached converter
                st.session_state.vanna_converter = get_vanna_converter(
                    database_url, openai_api_key, config_hash
                )
                progress_bar.progress(75)
                
                # Store config hash to avoid reinitializing
                st.session_state.vanna_config_hash = config_hash
                progress_bar.progress(100)
                
                # Clear initialization UI
                init_placeholder.empty()
                progress_bar.empty()
                
                logger.info("VannaTextToSQLConverter inicializado com sucesso")
                st.success("✅ Vanna.ai inicializado com sucesso!")
                
            except Exception as init_error:
                progress_bar.empty()
                init_placeholder.empty()
                raise init_error
        else:
            # Already initialized with same config
            logger.info("Vanna.ai já inicializado (usando cache)")
        
        # Main query interface
        st.markdown("---")
        
        # Text input for user question
        user_question = st.text_area(
            "💬 **Faça sua pergunta em português:**",
            placeholder="Ex: Mostre todas as notas fiscais dos últimos 30 dias",
            height=80
        )
        
        # Process query button
        if st.button("🔍 **Consultar com Vanna.ai**", type="primary", use_container_width=True):
            if user_question.strip():
                logger.info(f"Processando pergunta com Vanna.ai: {user_question[:100]}...")
                
                # Create progress tracking
                query_placeholder = st.empty()
                query_progress = st.progress(0)
                
                with query_placeholder.container():
                    st.info("🤖 Processando com Vanna.ai...")
                    st.caption("Gerando consulta SQL inteligente")
                
                query_progress.progress(20)
                
                try:
                    start_time = datetime.now()
                    query_progress.progress(50)
                    
                    result = st.session_state.vanna_converter.process_question(user_question)
                    
                    query_progress.progress(90)
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    # Clear progress UI
                    query_placeholder.empty()
                    query_progress.progress(100)
                    query_progress.empty()
                    
                    logger.info(f"Pergunta processada em {processing_time:.2f} segundos")
                
                except Exception as query_error:
                    query_placeholder.empty()
                    query_progress.empty()
                    st.error(f"❌ **Erro:** {str(query_error)}")
                    logger.error(f"Erro durante processamento: {str(query_error)}")
                    result = {"success": False, "error": str(query_error), "sql_query": None, "result": None}
                
                if result["success"]:
                    # Display results first (more important)
                    st.success("✅ **Consulta executada com sucesso!**")
                    logger.info(f"Consulta executada com sucesso. Registros encontrados: {len(result['result']) if result['result'] is not None else 0}")
                    
                    if result["result"] is not None and not result["result"].empty:
                        st.dataframe(
                            result["result"],
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Show summary
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("📊 Registros encontrados", len(result['result']))
                        with col2:
                            csv = result["result"].to_csv(index=False)
                            st.download_button(
                                label="📥 Baixar CSV",
                                data=csv,
                                file_name="consulta_notas_fiscais_vanna.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        
                        # Show SQL query in expander (less prominent)
                        with st.expander("🔍 Ver consulta SQL gerada pela Vanna.ai"):
                            st.code(result["sql_query"], language="sql")
                    else:
                        st.info("🔍 Consulta executada, mas nenhum resultado encontrado.")
                        with st.expander("🔍 Ver consulta SQL gerada pela Vanna.ai"):
                            st.code(result["sql_query"], language="sql")
                else:
                    st.error(f"❌ **Erro:** {result['error']}")
                    logger.error(f"Erro ao processar consulta: {result['error']}")
                    if result["sql_query"]:
                        with st.expander("🔍 Ver consulta SQL (falhou)"):
                            st.code(result["sql_query"], language="sql")
            else:
                st.warning("⚠️ Por favor, digite uma pergunta para consultar.")
                logger.warning("Tentativa de consulta com pergunta vazia")
        
        # Training section
        st.markdown("---")
        st.subheader("🧠 Treinamento do Vanna.ai")
        
        with st.expander("📚 Treinar com Exemplo", expanded=False):
            st.info("💡 Melhore a precisão do Vanna.ai adicionando exemplos de perguntas e consultas SQL")
            
            col1, col2 = st.columns(2)
            with col1:
                training_question = st.text_area(
                    "Pergunta em português:",
                    placeholder="Ex: Quais são os top 5 restaurantes por faturamento?",
                    height=60
                )
            with col2:
                training_sql = st.text_area(
                    "Consulta SQL correspondente:",
                    placeholder="SELECT vendor_name, SUM(total_amount) FROM extracted_invoices GROUP BY vendor_name ORDER BY SUM(total_amount) DESC LIMIT 5",
                    height=60
                )
            
            if st.button("🧠 **Treinar Vanna.ai**", use_container_width=True):
                if training_question.strip() and training_sql.strip():
                    train_placeholder = st.empty()
                    train_progress = st.progress(0)
                    
                    with train_placeholder.container():
                        st.info("🧠 Treinando modelo...")
                        st.caption("Adicionando novo conhecimento ao Vanna.ai")
                    
                    train_progress.progress(50)
                    
                    try:
                        train_result = st.session_state.vanna_converter.train_model(training_question, training_sql)
                        train_progress.progress(100)
                        
                        # Clear training UI
                        train_placeholder.empty()
                        train_progress.empty()
                    except Exception as train_error:
                        train_placeholder.empty()
                        train_progress.empty()
                        st.error(f"❌ Erro no treinamento: {str(train_error)}")
                        logger.error(f"Erro no treinamento: {str(train_error)}")
                        train_result = {"success": False, "error": str(train_error)}
                    
                    if train_result["success"]:
                        st.success("✅ Modelo treinado com sucesso!")
                        logger.info(f"Modelo treinado com pergunta: {training_question[:50]}...")
                    else:
                        st.error(f"❌ Erro no treinamento: {train_result['error']}")
                        logger.error(f"Erro no treinamento: {train_result['error']}")
                else:
                    st.warning("⚠️ Preencha tanto a pergunta quanto a consulta SQL.")
        
    except Exception as e:
        error_msg = str(e)
        
        # Provide more specific error messages
        if "tenant" in error_msg.lower():
            st.error("❌ **Erro de inicialização do ChromaDB**")
            st.info("💡 Problema comum na primeira inicialização. Vamos tentar resolver automaticamente.")
            
            # Auto-cleanup and retry
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🗑️ Limpar Cache"):
                    try:
                        # Clear ChromaDB cache directories
                        cache_dirs = ['./vanna_chromadb', './vanna_chromadb_*']
                        for cache_dir in cache_dirs:
                            if os.path.exists(cache_dir):
                                shutil.rmtree(cache_dir)
                        
                        # Clear Streamlit cache
                        st.cache_resource.clear()
                        st.success("✅ Cache limpo! Recarregue a página.")
                        st.rerun()
                    except Exception as clean_error:
                        st.error(f"Erro ao limpar cache: {clean_error}")
                        
            with col2:
                if st.button("🔄 Tentar Novamente"):
                    st.cache_resource.clear()
                    st.experimental_rerun()
                    
            with col3:
                if st.button("📄 Recarregar Página"):
                    st.experimental_rerun()
                    
        elif "api" in error_msg.lower():
            st.error("❌ **Erro na API OpenAI**")
            st.info("💡 Verifique sua chave da API OpenAI na configuração acima.")
        else:
            st.error(f"❌ **Erro ao conectar:** {error_msg}")
            st.info("💡 Verifique sua chave da API OpenAI e tente novamente.")
            
        logger.error(f"Erro ao inicializar aplicação: {str(e)}")

else:
    st.warning("⚠️ **Configure sua chave da API OpenAI** na seção de configuração acima para começar.")
    logger.warning("Aplicação iniciada sem chave OpenAI configurada")
    
    # Simplified info
    st.info("""
    **🍔 UberEats Brasil - Sistema com Vanna.ai**
    
    Este sistema usa Vanna.ai, um agente SQL AI de última geração para consultar dados de notas fiscais.
    
    📝 **Como usar:**
    1. Configure sua chave da API OpenAI
    2. Digite sua pergunta em português 
    3. Clique em "Consultar com Vanna.ai"
    4. Opcionalmente, treine o modelo com novos exemplos
    
    🚀 **Vantagens do Vanna.ai:**
    - RAG (Retrieval Augmented Generation) para maior precisão
    - Treinamento contínuo do modelo
    - Segurança: dados do banco não são enviados para LLM
    - Open-source e personalizável
    - Cache inteligente para melhor performance
    
    🔒 **Seguro:** Apenas consultas de leitura são permitidas
    """)

# Footer with Vanna.ai branding using settings
st.markdown("---")
st.markdown(f"{settings.app_icon} **{settings.app_title}** | 🤖 **Powered by Vanna.ai** | Sistema de Consultas Inteligentes")