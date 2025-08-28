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

from core.multi_db_converter import MultiDatabaseVannaConverter, DatabaseType
from config.settings import get_settings
from dotenv import load_dotenv
import hashlib
import shutil
import json

load_dotenv()

# Get application settings
settings = get_settings()

# Configure logging using settings
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file_multi_db),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure Streamlit page using settings
st.set_page_config(
    page_title=f"{settings.app_title} - Multi-Database Query System",
    page_icon=settings.app_icon,
    layout="wide"
)

# Header using settings
st.title(f"{settings.app_icon} {settings.app_title} - Sistema Multi-Database")
st.subheader("🔄 PostgreSQL + Qdrant Vector Search")
st.caption("🤖 Powered by Vanna.ai + Qdrant - Sistema Inteligente de Consultas")

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
    
    # Database status
    st.subheader("📊 Status das Conexões")
    if 'multi_converter' in st.session_state:
        try:
            db_info = st.session_state.multi_converter.get_database_info()
            
            for db_name, info in db_info["databases"].items():
                if info["status"] == "connected":
                    st.success(f"✅ {db_name.title()}: Conectado")
                    if db_name == "postgresql" and "tables" in info:
                        st.caption(f"📋 {len(info['tables'])} tabelas")
                    elif db_name == "qdrant" and "collections" in info:
                        st.caption(f"🗂️ {len(info['collections'])} collections")
                else:
                    st.error(f"❌ {db_name.title()}: {info['status']}")
        except Exception as e:
            st.warning(f"⚠️ Erro ao verificar status: {e}")

# Initialize the multi-database converter
if openai_api_key and postgres_url and qdrant_url and qdrant_api_key:
    # Create configuration hash to detect changes
    config_hash = hashlib.md5(
        f"{openai_api_key[:10]}{postgres_url[:20]}{qdrant_url[:20]}{qdrant_api_key[:10]}".encode()
    ).hexdigest()
    
    try:
        # Cache the converter
        @st.cache_resource(show_spinner=False)
        def get_multi_converter(_postgres_url, _qdrant_url, _qdrant_api_key, _openai_api_key, _config_hash):
            """Cached multi-database converter initialization"""
            return MultiDatabaseVannaConverter(
                postgres_url=_postgres_url,
                qdrant_url=_qdrant_url,
                qdrant_api_key=_qdrant_api_key,
                openai_api_key=_openai_api_key
            )
        
        # Check if we need to reinitialize
        if ('multi_converter' not in st.session_state or 
            st.session_state.get('multi_config_hash') != config_hash):
            
            logger.info("Inicializando MultiDatabaseVannaConverter")
            
            # Show initialization progress
            init_placeholder = st.empty()
            progress_bar = st.progress(0)
            
            with init_placeholder.container():
                st.info("🔄 Inicializando Sistema Multi-Database...")
                st.caption("Esta operação pode levar alguns segundos")
            
            progress_bar.progress(20)
            
            try:
                # Initialize converter
                st.session_state.multi_converter = get_multi_converter(
                    postgres_url, qdrant_url, qdrant_api_key, openai_api_key, config_hash
                )
                progress_bar.progress(80)
                
                st.session_state.multi_config_hash = config_hash
                progress_bar.progress(100)
                
                # Clear initialization UI
                init_placeholder.empty()
                progress_bar.empty()
                
                logger.info("MultiDatabaseVannaConverter inicializado com sucesso")
                st.success("✅ Sistema Multi-Database inicializado!")
                
            except Exception as init_error:
                progress_bar.empty()
                init_placeholder.empty()
                st.error(f"❌ Erro na inicialização: {init_error}")
                logger.error(f"Erro na inicialização: {init_error}")
                st.stop()
        else:
            logger.info("Sistema já inicializado (usando cache)")
        
        # Main interface with tabs
        tab1, tab2, tab3 = st.tabs(["🔍 Consultar", "🧠 Treinar", "📊 Inserir Dados"])
        
        with tab1:
            st.markdown("### 💬 Faça sua Pergunta")
            
            # Query type selection
            col1, col2 = st.columns([3, 1])
            with col1:
                user_question = st.text_area(
                    "Digite sua pergunta:",
                    placeholder="Ex: Mostre as últimas 10 notas fiscais OU Encontre documentos similares a 'pizza delivery'",
                    height=100
                )
            
            with col2:
                query_mode = st.selectbox(
                    "🎯 Modo de Consulta",
                    ["🤖 Automático", "🗄️ PostgreSQL", "🔍 Qdrant"],
                    help="Automático detecta o melhor banco baseado na pergunta"
                )
                
                if query_mode == "🔍 Qdrant":
                    limit = st.number_input("Limite de resultados", min_value=1, max_value=100, value=10)
            
            # Query examples
            with st.expander("💡 Exemplos de Perguntas"):
                st.markdown("""
                **Para PostgreSQL (Dados Estruturados):**
                - "Mostre todas as notas fiscais dos últimos 30 dias"
                - "Qual é o total de faturamento por restaurante?"
                - "Quantas notas fiscais estão pendentes?"
                
                **Para Qdrant (Busca Vetorial):**
                - "Encontre documentos similares a 'entrega de pizza'"
                - "Busque itens parecidos com 'hambúrguer gourmet'"
                - "Documentos relacionados a 'delivery noturno'"
                """)
            
            # Process query
            if st.button("🚀 **Executar Consulta**", type="primary", use_container_width=True):
                if user_question.strip():
                    logger.info(f"Processando pergunta: {user_question[:100]}...")
                    
                    # Show progress
                    query_placeholder = st.empty()
                    query_progress = st.progress(0)
                    
                    with query_placeholder.container():
                        st.info("🔄 Processando consulta...")
                        
                        # Show which database will be used
                        if query_mode == "🤖 Automático":
                            detected_db = st.session_state.multi_converter._detect_query_type(user_question)
                            st.caption(f"🎯 Detectado: {detected_db.value.title()}")
                        elif query_mode == "🗄️ PostgreSQL":
                            st.caption("🗄️ Usando PostgreSQL")
                        else:
                            st.caption("🔍 Usando Qdrant")
                    
                    query_progress.progress(30)
                    
                    try:
                        start_time = datetime.now()
                        
                        # Execute query based on mode
                        if query_mode == "🤖 Automático":
                            result = st.session_state.multi_converter.process_question(user_question)
                        elif query_mode == "🗄️ PostgreSQL":
                            result = st.session_state.multi_converter.query_postgresql(user_question)
                        else:  # Qdrant
                            result = st.session_state.multi_converter.query_qdrant(user_question, limit=limit)
                        
                        query_progress.progress(90)
                        processing_time = (datetime.now() - start_time).total_seconds()
                        
                        # Clear progress UI
                        query_placeholder.empty()
                        query_progress.progress(100)
                        query_progress.empty()
                        
                        logger.info(f"Pergunta processada em {processing_time:.2f}s")
                        
                        # Display results
                        if result.success:
                            st.success(f"✅ **Consulta executada com sucesso!** ({result.database_type.value.title()})")
                            
                            if result.data is not None and not result.data.empty:
                                # Show results
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
                                    st.metric("🗄️ Database", result.database_type.value.title())
                                
                                # Download option
                                csv = result.data.to_csv(index=False)
                                st.download_button(
                                    label="📥 Baixar CSV",
                                    data=csv,
                                    file_name=f"consulta_{result.database_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv"
                                )
                                
                                # Show query details
                                if result.query:
                                    with st.expander(f"🔍 Ver consulta ({result.database_type.value.title()})"):
                                        if result.database_type == DatabaseType.POSTGRESQL:
                                            st.code(result.query, language="sql")
                                        else:
                                            st.text(result.query)
                            else:
                                st.info("🔍 Consulta executada, mas nenhum resultado encontrado.")
                                if result.query:
                                    with st.expander("🔍 Ver consulta"):
                                        st.text(result.query)
                        else:
                            st.error(f"❌ **Erro:** {result.error}")
                            if result.query:
                                with st.expander("🔍 Ver consulta (falhou)"):
                                    st.text(result.query)
                    
                    except Exception as query_error:
                        query_placeholder.empty()
                        query_progress.empty()
                        st.error(f"❌ **Erro:** {str(query_error)}")
                        logger.error(f"Erro durante consulta: {str(query_error)}")
                else:
                    st.warning("⚠️ Por favor, digite uma pergunta.")
        
        with tab2:
            st.markdown("### 🧠 Treinamento do Modelo")
            st.info("💡 Melhore a precisão das consultas PostgreSQL adicionando exemplos")
            
            col1, col2 = st.columns(2)
            with col1:
                training_question = st.text_area(
                    "Pergunta em português:",
                    placeholder="Ex: Quais são os top 5 restaurantes por faturamento?",
                    height=100
                )
            with col2:
                training_sql = st.text_area(
                    "SQL correspondente:",
                    placeholder="SELECT vendor_name, SUM(total_amount) FROM extracted_invoices GROUP BY vendor_name ORDER BY SUM(total_amount) DESC LIMIT 5",
                    height=100
                )
            
            if st.button("🧠 **Treinar Modelo**", use_container_width=True):
                if training_question.strip() and training_sql.strip():
                    train_result = st.session_state.multi_converter.train_model(training_question, training_sql)
                    
                    if train_result["success"]:
                        st.success("✅ Modelo treinado com sucesso!")
                    else:
                        st.error(f"❌ Erro: {train_result['error']}")
                else:
                    st.warning("⚠️ Preencha tanto a pergunta quanto o SQL.")
        
        with tab3:
            st.markdown("### 📊 Inserir Dados no Qdrant")
            st.info("💡 Adicione dados vetoriais ao Qdrant para busca por similaridade")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📝 Dados JSON")
                data_input = st.text_area(
                    "Cole dados JSON (lista de objetos):",
                    placeholder='[{"id": "1", "title": "Pizza Margherita", "description": "Pizza com molho de tomate e mozzarella"}, {"id": "2", "title": "Hambúrguer Clássico", "description": "Hambúrguer com carne, alface e tomate"}]',
                    height=200
                )
            
            with col2:
                st.subheader("⚙️ Opções")
                auto_embed = st.checkbox("🤖 Gerar embeddings automaticamente", value=True)
                embed_field = st.selectbox(
                    "Campo para embedding:",
                    ["description", "title", "combined"],
                    help="Campo que será usado para gerar os embeddings"
                )
            
            if st.button("📊 **Inserir no Qdrant**", use_container_width=True):
                if data_input.strip():
                    try:
                        # Parse JSON data
                        data = json.loads(data_input)
                        
                        if not isinstance(data, list):
                            st.error("❌ Os dados devem ser uma lista de objetos JSON")
                        else:
                            # Generate embeddings if requested
                            vectors = None
                            if auto_embed:
                                vectors = []
                                for item in data:
                                    if embed_field == "combined":
                                        text = f"{item.get('title', '')} {item.get('description', '')}"
                                    else:
                                        text = item.get(embed_field, '')
                                    
                                    vector = st.session_state.multi_converter._generate_embedding(text)
                                    vectors.append(vector)
                            
                            # Insert data
                            success = st.session_state.multi_converter.insert_to_qdrant(data, vectors)
                            
                            if success:
                                st.success(f"✅ {len(data)} itens inseridos no Qdrant!")
                            else:
                                st.error("❌ Erro ao inserir dados no Qdrant")
                    
                    except json.JSONDecodeError:
                        st.error("❌ Formato JSON inválido")
                    except Exception as e:
                        st.error(f"❌ Erro: {e}")
                else:
                    st.warning("⚠️ Cole os dados JSON para inserir.")
    
    except Exception as e:
        st.error(f"❌ **Erro de inicialização:** {str(e)}")
        
        # Error recovery options
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🗑️ Limpar Cache"):
                st.cache_resource.clear()
                st.success("✅ Cache limpo! Recarregue a página.")
        
        with col2:
            if st.button("🔄 Tentar Novamente"):
                st.rerun()
        
        with col3:
            if st.button("📄 Recarregar Página"):
                st.rerun()
        
        logger.error(f"Erro na aplicação: {str(e)}")

else:
    st.warning("⚠️ **Configure todas as credenciais** na barra lateral para começar.")
    
    # Information about the system
    st.info("""
    **🍔 UberEats Brasil - Sistema Multi-Database**
    
    Este sistema combina:
    - **PostgreSQL**: Dados estruturados (notas fiscais, restaurantes)
    - **Qdrant**: Busca vetorial e similaridade semântica
    
    📝 **Recursos:**
    - Detecção automática do tipo de consulta
    - Consultas SQL inteligentes com Vanna.ai
    - Busca por similaridade vetorial
    - Treinamento contínuo do modelo
    - Interface multi-database unificada
    
    🚀 **Vantagens:**
    - Melhor dos dois mundos: SQL estruturado + busca semântica
    - IA que aprende com o uso
    - Segurança: apenas consultas de leitura
    - Performance otimizada com cache
    """)

# Footer using settings
st.markdown("---")
st.markdown(f"{settings.app_icon} **{settings.app_title}** | 🤖 **Vanna.ai + Qdrant** | Sistema Multi-Database Inteligente")