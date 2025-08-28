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

from core.cross_db_converter import EnhancedVannaConverter, QueryType
from config.settings import get_settings
from dotenv import load_dotenv
import hashlib

load_dotenv()

# Get application settings
settings = get_settings()

# Configure logging using settings
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file_cross_db),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure Streamlit page using settings
st.set_page_config(
    page_title=f"{settings.app_title} - Cross-Database AI System",
    page_icon=settings.app_icon,
    layout="wide"
)

# Header using settings
st.title(f"{settings.app_icon} {settings.app_title} - Sistema Cross-Database")
st.subheader("🔄 Menu (Qdrant) + Faturamento (PostgreSQL)")
st.caption("🤖 Powered by Enhanced Vanna.ai - Consultas Inteligentes Cross-Database")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuração")
    
    # Database configurations
    st.subheader("🗄️ PostgreSQL")
    postgres_url = st.text_input(
        "URL PostgreSQL",
        value=settings.database_url,
        type="password"
    )
    
    st.subheader("🔍 Qdrant Vector DB")
    qdrant_url = st.text_input(
        "URL Qdrant",
        value=settings.qdrant_url,
        type="password"
    )
    
    qdrant_api_key = st.text_input(
        "Qdrant API Key",
        value=settings.qdrant_api_key,
        type="password"
    )
    
    st.subheader("🤖 OpenAI")
    openai_api_key = st.text_input(
        "OpenAI API Key",
        value=settings.openai_api_key or "",
        type="password"
    )

# Initialize the enhanced converter
if openai_api_key and postgres_url and qdrant_url and qdrant_api_key:
    # Create configuration hash
    config_hash = hashlib.md5(
        f"{openai_api_key[:10]}{postgres_url[:20]}{qdrant_url[:20]}{qdrant_api_key[:10]}".encode()
    ).hexdigest()
    
    try:
        # Cache the enhanced converter
        @st.cache_resource(show_spinner=False)
        def get_enhanced_converter(_postgres_url, _qdrant_url, _qdrant_api_key, _openai_api_key, _config_hash):
            """Cached enhanced converter initialization"""
            return EnhancedVannaConverter(
                postgres_url=_postgres_url,
                qdrant_url=_qdrant_url,
                qdrant_api_key=_qdrant_api_key,
                openai_api_key=_openai_api_key
            )
        
        # Check if we need to reinitialize
        if ('enhanced_converter' not in st.session_state or 
            st.session_state.get('enhanced_config_hash') != config_hash):
            
            logger.info("Inicializando EnhancedVannaConverter")
            
            # Show initialization progress
            init_placeholder = st.empty()
            progress_bar = st.progress(0)
            
            with init_placeholder.container():
                st.info("🔄 Inicializando Sistema Cross-Database Enhanced...")
                st.caption("Esta operação pode levar alguns segundos")
            
            progress_bar.progress(20)
            
            try:
                # Initialize enhanced converter
                st.session_state.enhanced_converter = get_enhanced_converter(
                    postgres_url, qdrant_url, qdrant_api_key, openai_api_key, config_hash
                )
                progress_bar.progress(80)
                
                st.session_state.enhanced_config_hash = config_hash
                progress_bar.progress(100)
                
                # Clear initialization UI
                init_placeholder.empty()
                progress_bar.empty()
                
                logger.info("EnhancedVannaConverter inicializado com sucesso")
                st.success("✅ Sistema Cross-Database Enhanced inicializado!")
                
            except Exception as init_error:
                progress_bar.empty()
                init_placeholder.empty()
                st.error(f"❌ Erro na inicialização: {init_error}")
                logger.error(f"Erro na inicialização: {init_error}")
                st.stop()
        else:
            logger.info("Sistema já inicializado (usando cache)")
        
        # Main interface
        st.markdown("---")
        st.markdown("### 💬 Faça sua Pergunta Cross-Database")
        
        # Query examples
        with st.expander("💡 Exemplos de Perguntas Cross-Database"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **🔄 Cross-Database (Menu + Faturamento):**
                - "Mostre o faturamento dos restaurantes mexicanos"
                - "Qual é o ticket médio dos restaurantes vegetarianos?"
                - "Faturamento dos restaurantes que servem entradas"
                - "Performance dos restaurantes sem glúten"
                """)
            
            with col2:
                st.markdown("""
                **🗄️ Só PostgreSQL (Faturamento):**
                - "Mostre as últimas 10 notas fiscais"
                - "Qual é o faturamento total este mês?"
                - "Top 5 restaurantes por vendas"
                - "Ticket médio geral"
                """)
        
        # Query input
        user_question = st.text_area(
            "Digite sua pergunta:",
            placeholder="Ex: Mostre o faturamento dos restaurantes mexicanos nos últimos 30 dias",
            height=100
        )
        
        # Process query
        if st.button("🚀 **Executar Consulta Cross-Database**", type="primary", use_container_width=True):
            if user_question.strip():
                logger.info(f"Processando pergunta cross-database: {user_question[:100]}...")
                
                # Show progress
                query_placeholder = st.empty()
                query_progress = st.progress(0)
                
                with query_placeholder.container():
                    st.info("🔄 Analisando pergunta...")
                    st.caption("Detectando se precisa de dados de menu + faturamento")
                
                query_progress.progress(20)
                
                try:
                    start_time = datetime.now()
                    
                    # Process with enhanced converter
                    result = st.session_state.enhanced_converter.process_question(user_question)
                    
                    query_progress.progress(90)
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    # Clear progress UI
                    query_placeholder.empty()
                    query_progress.progress(100)
                    query_progress.empty()
                    
                    logger.info(f"Pergunta processada em {processing_time:.2f}s")
                    
                    # Display results
                    if result.success:
                        st.success(f"✅ **Consulta executada com sucesso!**")
                        
                        # Show execution plan
                        if result.execution_plan:
                            st.info(f"📋 **Plano de Execução:** {result.execution_plan}")
                            
                            if result.restaurants_found is not None:
                                st.caption(f"🔍 Restaurantes encontrados no Qdrant: {result.restaurants_found}")
                        
                        # Show results
                        if result.data is not None and not result.data.empty:
                            st.dataframe(
                                result.data,
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            # Metrics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("📊 Registros", len(result.data))
                            with col2:
                                st.metric("⏱️ Tempo", f"{processing_time:.2f}s")
                            with col3:
                                if result.restaurants_found is not None:
                                    st.metric("🏪 Restaurantes", result.restaurants_found)
                                else:
                                    st.metric("🗄️ Fonte", "PostgreSQL")
                            
                            # Download option
                            csv = result.data.to_csv(index=False)
                            st.download_button(
                                label="📥 Baixar CSV",
                                data=csv,
                                file_name=f"consulta_cross_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                        else:
                            st.info("🔍 Consulta executada, mas nenhum resultado encontrado.")
                            if result.restaurants_found == 0:
                                st.warning("⚠️ Nenhum restaurante encontrado com os critérios de menu especificados.")
                        
                        # Show query details
                        if result.query:
                            with st.expander("🔍 Ver consulta executada"):
                                if result.qdrant_filter_used:
                                    st.markdown("**🔍 Filtro Qdrant (Menu):**")
                                    st.code(f"Critério: {result.qdrant_filter_used}", language="text")
                                    st.markdown("**🗄️ SQL PostgreSQL (Faturamento):**")
                                
                                st.code(result.query, language="sql")
                    else:
                        st.error(f"❌ **Erro:** {result.error}")
                        if result.query:
                            with st.expander("🔍 Ver consulta (falhou)"):
                                st.code(result.query, language="sql")
                
                except Exception as query_error:
                    query_placeholder.empty()
                    query_progress.empty()
                    st.error(f"❌ **Erro:** {str(query_error)}")
                    logger.error(f"Erro durante consulta cross-database: {str(query_error)}")
            else:
                st.warning("⚠️ Por favor, digite uma pergunta.")
        
        # Training section
        st.markdown("---")
        st.markdown("### 🧠 Treinamento do Modelo")
        
        with st.expander("📚 Treinar com Exemplo SQL", expanded=False):
            st.info("💡 Melhore a precisão das consultas PostgreSQL adicionando exemplos")
            
            col1, col2 = st.columns(2)
            with col1:
                training_question = st.text_area(
                    "Pergunta em português:",
                    placeholder="Ex: Qual é o faturamento total dos restaurantes?",
                    height=80
                )
            with col2:
                training_sql = st.text_area(
                    "SQL correspondente:",
                    placeholder="SELECT SUM(total_amount) FROM extracted_invoices",
                    height=80
                )
            
            if st.button("🧠 **Treinar Modelo**", use_container_width=True):
                if training_question.strip() and training_sql.strip():
                    train_result = st.session_state.enhanced_converter.train_model(training_question, training_sql)
                    
                    if train_result["success"]:
                        st.success("✅ Modelo treinado com sucesso!")
                    else:
                        st.error(f"❌ Erro: {train_result['error']}")
                else:
                    st.warning("⚠️ Preencha tanto a pergunta quanto o SQL.")
        
        # Database info
        with st.sidebar:
            st.markdown("---")
            st.subheader("📊 Status do Sistema")
            
            try:
                db_info = st.session_state.enhanced_converter.get_database_info()
                
                # PostgreSQL status
                pg_status = db_info["databases"]["postgresql"]["status"]
                if pg_status == "connected":
                    st.success("✅ PostgreSQL: Conectado")
                else:
                    st.error(f"❌ PostgreSQL: {pg_status}")
                
                # Qdrant status
                qdrant_status = db_info["databases"]["qdrant"]["status"]
                if qdrant_status == "connected":
                    st.success("✅ Qdrant: Conectado")
                    if "collections" in db_info["databases"]["qdrant"]:
                        collections = db_info["databases"]["qdrant"]["collections"]
                        st.caption(f"🗂️ Collections: {len(collections)}")
                else:
                    st.error(f"❌ Qdrant: {qdrant_status}")
                
                # Cross-database patterns
                if "cross_database_patterns" in db_info:
                    st.markdown("**🔄 Padrões Suportados:**")
                    for pattern in db_info["cross_database_patterns"]:
                        st.caption(f"• {pattern}")
                
            except Exception as e:
                st.warning(f"⚠️ Erro ao verificar status: {e}")

    except Exception as e:
        st.error(f"❌ **Erro de inicialização:** {str(e)}")
        
        # Error recovery options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Limpar Cache"):
                st.cache_resource.clear()
                st.success("✅ Cache limpo! Recarregue a página.")
        
        with col2:
            if st.button("🔄 Tentar Novamente"):
                st.rerun()
        
        logger.error(f"Erro na aplicação cross-database: {str(e)}")

else:
    st.warning("⚠️ **Configure todas as credenciais** na barra lateral para começar.")
    
    # Information about the enhanced system
    st.info("""
    **🍔 UberEats Brasil - Sistema Cross-Database Enhanced**
    
    Este sistema combina dados de **menu (Qdrant)** com **faturamento (PostgreSQL)**:
    
    🔄 **Capacidades Cross-Database:**
    - Detecta automaticamente se a pergunta precisa de dados de menu + faturamento
    - Filtra restaurantes no Qdrant baseado em critérios de cardápio
    - Executa análise financeira no PostgreSQL para restaurantes filtrados
    - Combina resultados de forma inteligente
    
    🎯 **Exemplos de Uso:**
    - "Faturamento dos restaurantes mexicanos" → Qdrant + PostgreSQL
    - "Ticket médio dos restaurantes vegetarianos" → Qdrant + PostgreSQL  
    - "Últimas 10 notas fiscais" → Só PostgreSQL
    
    🚀 **Tecnologia:**
    - Vanna.ai para geração de SQL
    - Qdrant para busca de menu/cardápio
    - PostgreSQL para dados financeiros
    - IA que detecta automaticamente o tipo de consulta
    """)

# Footer using settings
st.markdown("---")
st.markdown(f"{settings.app_icon} **{settings.app_title}** | 🤖 **Enhanced Vanna.ai** | Sistema Cross-Database Inteligente")