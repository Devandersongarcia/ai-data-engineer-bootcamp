import streamlit as st
import os
import logging
from datetime import datetime
from text_to_sql import TextToSQLConverter
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../../ubereats_brasil.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="UberEats Brasil - Consulta de Notas Fiscais",
    page_icon="🍔",
    layout="centered"
)

# Simple header
st.title("🍔 UberEats Brasil")
st.subheader("Consulta Inteligente de Notas Fiscais")

# Simplified configuration in main area
with st.expander("⚙️ Configuração", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        openai_api_key = st.text_input(
            "Chave OpenAI API",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password"
        )
    with col2:
        database_url = st.text_input(
            "URL do Banco",
            value=os.getenv("DATABASE_URL", ""),
            type="password"
        )

# Initialize the converter
if openai_api_key and database_url:
    try:
        if 'converter' not in st.session_state:
            logger.info("Inicializando TextToSQLConverter")
            st.session_state.converter = TextToSQLConverter(
                database_url=database_url,
                openai_api_key=openai_api_key
            )
            logger.info("TextToSQLConverter inicializado com sucesso")
        
        # Main query interface
        st.markdown("---")
        
        # Text input for user question
        user_question = st.text_area(
            "💬 **Faça sua pergunta em português:**",
            placeholder="Ex: Mostre todas as notas fiscais dos últimos 30 dias",
            height=80
        )
        
        
        # Process query button
        if st.button("🔍 **Consultar Dados**", type="primary", use_container_width=True):
            if user_question.strip():
                logger.info(f"Processando pergunta: {user_question[:100]}...")
                with st.spinner("🤖 Processando sua pergunta..."):
                    start_time = datetime.now()
                    result = st.session_state.converter.process_question(
                        user_question, 
                        user_id="streamlit_user"
                    )
                    processing_time = (datetime.now() - start_time).total_seconds()
                    logger.info(f"Pergunta processada em {processing_time:.2f} segundos")
                
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
                        
                        # Show summary with metrics
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("📊 Registros", len(result['result']))
                        with col2:
                            token_usage = result.get('token_usage')
                            if token_usage:
                                total_tokens = token_usage.get('total_tokens', 0)
                                st.metric("🔤 Tokens", total_tokens)
                            else:
                                st.metric("🔤 Tokens", "N/A")
                        with col3:
                            estimated_cost = result.get('estimated_cost')
                            if estimated_cost:
                                st.metric("💰 Custo", f"${estimated_cost:.6f}")
                            else:
                                st.metric("💰 Custo", "N/A")
                        with col4:
                            total_time = result.get('total_time', processing_time)
                            st.metric("⏱️ Tempo", f"{total_time:.2f}s")
                        
                        # Download button
                        csv = result["result"].to_csv(index=False)
                        st.download_button(
                            label="📥 Baixar CSV",
                            data=csv,
                            file_name="consulta_notas_fiscais.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        # Show SQL query in expander (less prominent)
                        with st.expander("🔍 Ver consulta SQL gerada"):
                            st.code(result["sql_query"], language="sql")
                        
                        # Show tracing information if available
                        if result.get('session_id'):
                            with st.expander("📈 Informações de Rastreamento"):
                                st.write("**Rastreamento Langfuse Ativo** 🎯")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write("**Sessão:**", result.get('session_id', 'N/A')[:20] + "...")
                                    st.write("**Geração SQL:**", str(result.get('sql_trace_id', 'N/A'))[:20] + "...")
                                    st.write("**Query BD:**", str(result.get('db_trace_id', 'N/A'))[:20] + "...")
                                
                                with col2:
                                    sql_time = result.get('sql_generation_time', 0)
                                    db_time = result.get('db_execution_time', 0)
                                    if sql_time:
                                        st.write(f"**Tempo SQL:** {sql_time:.3f}s")
                                    if db_time:
                                        st.write(f"**Tempo BD:** {db_time:.3f}s")
                                    if token_usage:
                                        st.write(f"**Tokens Entrada:** {token_usage.get('input_tokens', 0)}")
                                        st.write(f"**Tokens Saída:** {token_usage.get('output_tokens', 0)}")
                                
                                st.info("🌐 Veja análises detalhadas em: https://us.cloud.langfuse.com")
                    else:
                        st.info("🔍 Consulta executada, mas nenhum resultado encontrado.")
                        with st.expander("🔍 Ver consulta SQL gerada"):
                            st.code(result["sql_query"], language="sql")
                        
                        # Show tracing info for no results case
                        if result.get('session_id'):
                            with st.expander("📈 Informações de Rastreamento"):
                                st.write("**Rastreamento Langfuse Ativo** 🎯")
                                st.write("**Sessão:**", result.get('session_id', 'N/A')[:20] + "...")
                                token_usage = result.get('token_usage')
                                if token_usage:
                                    st.write(f"**Tokens Usados:** {token_usage.get('total_tokens', 0)}")
                                estimated_cost = result.get('estimated_cost')
                                if estimated_cost:
                                    st.write(f"**Custo Estimado:** ${estimated_cost:.6f}")
                                st.info("🌐 Veja análises detalhadas em: https://us.cloud.langfuse.com")
                else:
                    st.error(f"❌ **Erro:** {result['error']}")
                    logger.error(f"Erro ao processar consulta: {result['error']}")
                    
                    # Show metrics even for failed queries
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        token_usage = result.get('token_usage')
                        if token_usage and token_usage.get('total_tokens', 0) > 0:
                            st.metric("🔤 Tokens", token_usage.get('total_tokens', 0))
                        else:
                            st.metric("🔤 Tokens", "N/A")
                    with col2:
                        estimated_cost = result.get('estimated_cost')
                        if estimated_cost:
                            st.metric("💰 Custo", f"${estimated_cost:.6f}")
                        else:
                            st.metric("💰 Custo", "N/A")
                    with col3:
                        total_time = result.get('total_time', processing_time)
                        st.metric("⏱️ Tempo", f"{total_time:.2f}s")
                    
                    if result.get("sql_query"):
                        with st.expander("🔍 Ver consulta SQL (falhou)"):
                            st.code(result["sql_query"], language="sql")
                    
                    # Show tracing info for error case
                    if result.get('session_id'):
                        with st.expander("📈 Informações de Rastreamento (Erro)"):
                            st.write("**Rastreamento Langfuse Ativo** 🎯")
                            st.write("**Sessão:**", result.get('session_id', 'N/A')[:20] + "...")
                            if result.get('sql_trace_id'):
                                st.write("**Erro Rastreado:** ✅ Enviado para Langfuse")
                            st.info("🌐 Veja análises de erro em: https://us.cloud.langfuse.com")
            else:
                st.warning("⚠️ Por favor, digite uma pergunta para consultar.")
                logger.warning("Tentativa de consulta com pergunta vazia")
        
    except Exception as e:
        st.error(f"❌ **Erro ao conectar:** {str(e)}")
        st.info("💡 Verifique sua chave da API OpenAI na configuração acima.")
        logger.error(f"Erro ao inicializar aplicação: {str(e)}")

else:
    st.warning("⚠️ **Configure sua chave da API OpenAI** na seção de configuração acima para começar.")
    logger.warning("Aplicação iniciada sem chave OpenAI configurada")
    
    # Simplified info
    st.info("""
    **🍔 UberEats Brasil - Sistema de Consulta de Notas Fiscais**
    
    Este sistema permite consultar dados de notas fiscais de restaurantes usando linguagem natural em português.
    
    📝 **Como usar:**
    1. Configure sua chave da API OpenAI
    2. Digite sua pergunta em português 
    3. Clique em "Consultar Dados"
    
    🔒 **Seguro:** Apenas consultas de leitura são permitidas
    """)

# Simple footer
st.markdown("---")
st.markdown("🍔 **UberEats Brasil** | Sistema de Consultas Inteligentes")