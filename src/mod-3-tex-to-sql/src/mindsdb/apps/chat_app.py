"""
Brasil Invoice Expert - Chat Interface
Clean MindsDB implementation with structured architecture
"""
import streamlit as st
import sys
import os
from datetime import datetime
from typing import Optional

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mindsdb_client import connect
from config.settings import get_settings
from config.constants import UIText, QuickQuestions, AppConfig
from utils.logging_utils import get_logger
from utils.metrics import ChatMetrics, format_error_message, validate_connection_inputs
from utils.token_manager import create_token_manager
from utils.retry_utils import RetryContext

# Get settings and logger
settings = get_settings()
logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title=settings.app_title,
    page_icon=settings.app_icon,
    layout=settings.app_layout
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
# Limit chat history
if len(st.session_state.messages) > AppConfig.MAX_CHAT_HISTORY:
    st.session_state.messages = st.session_state.messages[-AppConfig.MAX_CHAT_HISTORY:]
    
if "mindsdb_server" not in st.session_state:
    st.session_state.mindsdb_server = None
    
if "agent" not in st.session_state:
    st.session_state.agent = None

# Initialize metrics and token manager
metrics = ChatMetrics()
token_manager = create_token_manager(settings.openai_model)

# Header
st.title(f"{settings.app_icon}🇧🇷 {settings.app_title}")
st.subheader(UIText.CHAT_SUBTITLE)

# Sidebar for connection
with st.sidebar:
    st.header(UIText.MINDSDB_CONNECTION_HEADER)
    
    # Server URL
    server_url = st.text_input(
        UIText.MINDSDB_SERVER_URL_LABEL,
        value=settings.mindsdb_server_url,
        help=UIText.MINDSDB_SERVER_HELP
    )
    
    # Agent selection - dynamic list or fallback to text input
    agent_name = None
    available_agents = []
    
    # Try to get available agents if server URL is provided
    if server_url and server_url.strip():
        # Cache agents list to avoid repeated calls
        cache_key = f"agents_{server_url}"
        
        if cache_key not in st.session_state or st.session_state.get('refresh_agents', False):
            try:
                with st.spinner(UIText.LOADING_AGENTS_MESSAGE):
                    from core.mindsdb_client import MindsDBServer
                    temp_server = MindsDBServer(server_url)
                    available_agents = temp_server.agents.list_agents()
                    
                    # Cache the result
                    st.session_state[cache_key] = available_agents
                    st.session_state['refresh_agents'] = False
                    
            except Exception as e:
                logger.debug(f"Could not load agents: {e}")
                available_agents = []
                st.session_state[cache_key] = []
        else:
            available_agents = st.session_state.get(cache_key, [])
    
    # Show agent selection
    if available_agents:
        # Use selectbox if agents are available
        default_index = 0
        if settings.agent_name in available_agents:
            default_index = available_agents.index(settings.agent_name)
        
        agent_name = st.selectbox(
            UIText.AGENT_NAME_LABEL,
            options=available_agents,
            index=default_index,
            help=UIText.AGENT_NAME_HELP,
            placeholder=UIText.AGENT_SELECTION_PLACEHOLDER
        )
        
        # Show agent description if available
        if agent_name and agent_name in UIText.AGENT_DESCRIPTIONS:
            st.info(UIText.AGENT_DESCRIPTIONS[agent_name])
        
        # Refresh button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button(UIText.REFRESH_AGENTS_BUTTON, use_container_width=True):
                st.session_state['refresh_agents'] = True
                st.rerun()
                
    else:
        # Fallback to text input if no agents found or server not accessible
        if server_url and server_url.strip():
            st.warning(UIText.NO_AGENTS_FOUND_MESSAGE)
        else:
            st.info(UIText.CONNECTION_REQUIRED_MESSAGE)
            
        agent_name = st.text_input(
            UIText.AGENT_NAME_LABEL,
            value=settings.agent_name,
            help=UIText.AGENT_NAME_HELP
        )
    
    # Connect button
    if st.button(UIText.CONNECT_BUTTON, use_container_width=True):
        # Validate inputs
        validation_error = validate_connection_inputs(server_url, agent_name)
        if validation_error:
            st.error(f"❌ {validation_error}")
        else:
            with st.spinner("Conectando ao MindsDB..."):
                try:
                    # Step 1: Connect to MindsDB
                    with st.status("Testando conexão...", expanded=True) as status:
                        st.write("🔗 Conectando ao servidor MindsDB...")
                        server = connect(server_url, timeout=settings.connection_timeout)
                        st.write(UIText.SERVER_REACHED)
                        
                        st.write(f"🤖 Buscando agente '{agent_name}'...")
                        agent = server.agents.get(agent_name)
                        st.write(UIText.AGENT_FOUND)
                        
                        status.update(label=UIText.CONNECTION_COMPLETE, state="complete")
                    
                    st.session_state.mindsdb_server = server
                    st.session_state.agent = agent
                    
                    st.success(UIText.CONNECTION_SUCCESS.format(agent_name))
                    st.info(UIText.READY_MESSAGE)
                    logger.info(f"Successfully connected to agent: {agent_name}")
                    
                except ConnectionError as e:
                    st.error(f"🔌 Erro de conexão: {str(e)}")
                    st.warning("""
                    **Servidor MindsDB inacessível:**
                    1. ✅ Verifique se MindsDB está rodando
                    2. 🌐 Confirme a URL do servidor
                    3. 🔥 Tente: `python -m mindsdb` para iniciar localmente
                    """)
                    logger.error(f"Connection failed: {e}")
                    
                except ValueError as e:
                    st.error(f"🤖 Erro do agente: {str(e)}")
                    st.warning("""
                    **Agente não encontrado:**
                    1. 📋 Execute `SHOW AGENTS;` no MindsDB Editor
                    2. 🛠️ Se não existir, execute o arquivo SQL de setup
                    3. 🔗 MindsDB Editor: http://127.0.0.1:47334
                    """)
                    logger.error(f"Agent error: {e}")
                    
                except Exception as e:
                    error_message = format_error_message(e)
                    st.error(f"❌ {error_message}")
                    logger.error(f"Unexpected connection error: {e}", exc_info=True)
                    
                finally:
                    if "server" not in locals() or "agent" not in locals():
                        st.session_state.agent = None
                        st.session_state.mindsdb_server = None
    
    # Connection status
    st.markdown("---")
    if st.session_state.agent:
        st.success(UIText.CONNECTED_STATUS)
        st.text(f"Agente: {agent_name}")
        
        # Show metrics
        if settings.enable_performance_tracking:
            with st.expander("📊 Estatísticas"):
                stats = metrics.get_stats()
                
                # Calculate token usage
                total_tokens = token_manager.count_message_tokens(st.session_state.messages)
                token_usage_pct = (total_tokens / token_manager.max_tokens) * 100
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Consultas", stats["total_queries"])
                    st.metric("Sucessos", stats["successful_queries"])
                with col2:
                    st.metric("Taxa Sucesso", f"{stats['success_rate']:.1f}%")
                    st.metric("Tempo Médio", f"{stats['average_response_time']:.1f}s")
                
                st.text(f"Sessão: {stats['session_duration']}")
                
                # Token usage indicator
                st.progress(min(token_usage_pct / 100, 1.0))
                st.text(f"Tokens: {total_tokens}/{token_manager.max_tokens} ({token_usage_pct:.1f}%)")
                
                if token_usage_pct > AppConfig.TOKEN_WARNING_THRESHOLD:
                    st.warning(UIText.HIGH_TOKEN_WARNING)
                
                # Connection pool statistics (if available)
                try:
                    from utils.connection_pool import get_pool_stats
                    pool_stats = get_pool_stats()
                    
                    st.markdown("**🔗 Pool de Conexões:**")
                    pool_col1, pool_col2 = st.columns(2)
                    with pool_col1:
                        st.metric("Conexões Ativas", pool_stats["active_sessions"])
                        st.metric("Hit Rate", f"{pool_stats['hit_rate']:.1f}%")
                    with pool_col2:
                        st.metric("Sessões Criadas", pool_stats["sessions_created"])
                        st.metric("Sessões Reutilizadas", pool_stats["sessions_reused"])
                        
                except (ImportError, Exception):
                    # Connection pooling not available or failed
                    pass
        
        # Disconnect button
        if st.button(UIText.DISCONNECT_BUTTON, use_container_width=True):
            # Clean up connection pool for the current server
            try:
                from utils.connection_pool import close_pooled_session
                close_pooled_session(server_url)
            except (ImportError, Exception):
                pass
            
            st.session_state.agent = None
            st.session_state.mindsdb_server = None
            st.session_state.messages = []
            st.rerun()
    else:
        st.error(UIText.DISCONNECTED_STATUS)
    
    # Quick setup guide
    st.markdown("---")
    st.subheader("🚀 Setup Rápido")
    with st.expander("📋 Como configurar"):
        st.markdown("""
        **Se o agente não existir:**
        
        1. **MindsDB Editor:** http://127.0.0.1:47334
        2. **Execute o arquivo SQL de setup** na pasta `sql/`
        3. **Configure suas credenciais** no arquivo `.env`
        4. **Verifique:**
           ```sql
           SHOW DATABASES;
           SHOW AGENTS;
           ```
        """)

# Main chat interface
if st.session_state.agent:
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input(UIText.CHAT_INPUT_PLACEHOLDER):
        # Check message length and truncate if needed
        if token_manager.count_tokens(prompt) > AppConfig.MAX_QUESTION_TOKENS:
            prompt = token_manager.truncate_text(prompt, AppConfig.MAX_QUESTION_TOKENS)
            st.warning(UIText.LONG_QUESTION_WARNING)
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Optimize conversation length to prevent token overflow
        if len(st.session_state.messages) > AppConfig.MAX_CONVERSATION_LENGTH:
            st.session_state.messages = token_manager.optimize_conversation(st.session_state.messages)
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner(UIText.THINKING_STATUS):
                # Start timing
                start_time = metrics.start_query()
                success = False
                response = ""
                
                try:
                    # Query the agent
                    completion = st.session_state.agent.completion(
                        messages=[{
                            'question': prompt,
                            'answer': None
                        }],
                        timeout=settings.chat_timeout
                    )
                    
                    # Extract the answer
                    if completion and len(completion) > 0:
                        response = completion[0].get('answer', 'Nenhuma resposta disponível')
                        success = True
                    else:
                        response = UIText.EMPTY_RESPONSE
                    
                    # Display response
                    st.markdown(response)
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    response = format_error_message(e)
                    st.error(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    # Show help for common errors
                    if "timeout" in str(e).lower():
                        st.info("💡 Dica: Pergunta muito complexa pode demorar. Tente simplificar.")
                    elif "conex" in str(e).lower():
                        st.info("💡 Dica: Verifique a conexão com o servidor MindsDB.")
                
                # End timing and log
                response_time = metrics.end_query(start_time, success)
                logger.info(f"Query processed in {response_time:.2f}s - Success: {success}")

else:
    # Welcome screen when not connected
    st.info("🔌 **Conecte-se ao MindsDB primeiro usando o painel lateral**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🧠 O que posso fazer:")
        st.markdown("""
        - **📊 Análise Financeira**
          - "Qual o faturamento total por estado?"
          - "Top 5 restaurantes por receita"
          - "Ticket médio por região"
        
        - **🏪 Dados de Restaurantes**  
          - "Quantos restaurantes únicos temos?"
          - "Restaurantes mais ativos por cidade"
          - "Análise de performance por estabelecimento"
        
        - **💳 Análise de Pagamentos**
          - "Métodos de pagamento mais usados"
          - "Gorjetas médias por tipo de pagamento"
          - "Tendências de pagamento por região"
        """)
    
    with col2:
        st.markdown("### 🧠 Como usar:")
        st.markdown("""
        1. **Configure a conexão** no painel lateral
        2. **Clique em "Conectar"** 
        3. **Comece a conversar!**
        
        ### 💡 Dicas:
        - Perguntas em **português** funcionam melhor
        - Seja **específico** sobre o que quer analisar
        - Peça para **gerar SQL** quando precisar
        - Use termos como "**Top 5**", "**por estado**"
        
        ### 🇧🇷 Contexto Tributário:
        O agente entende sobre **ICMS**, **ISS**, **PIS/COFINS** 
        e pode ajudar com análises fiscais brasileiras.
        """)

# Chat controls
if st.session_state.messages and st.session_state.agent:
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button(UIText.CLEAR_CHAT_BUTTON, use_container_width=True):
            st.session_state.messages = []
            st.success(UIText.CHAT_CLEARED)
            st.rerun()
    
    with col2:
        if st.button(UIText.STATUS_BUTTON, use_container_width=True):
            st.info(f"💬 {len(st.session_state.messages)} mensagens no chat")
    
    # Quick questions
    with col3:
        st.markdown(f"**{UIText.QUICK_QUESTIONS_HEADER}**")
        quick_cols = st.columns(3)
        
        with quick_cols[0]:
            if st.button(UIText.SUMMARY_BUTTON, key="quick1"):
                st.session_state.messages.append({"role": "user", "content": QuickQuestions.GENERAL_SUMMARY})
                st.rerun()
        
        with quick_cols[1]:
            if st.button(UIText.TOP5_BUTTON, key="quick2"):
                st.session_state.messages.append({"role": "user", "content": QuickQuestions.TOP5_RESTAURANTS})
                st.rerun()
        
        with quick_cols[2]:
            if st.button(UIText.STATES_BUTTON, key="quick3"):
                st.session_state.messages.append({"role": "user", "content": QuickQuestions.STATES_ANALYSIS})
                st.rerun()

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666;'>
    <p>{settings.app_icon} {settings.app_title} | MindsDB Python SDK | 🇧🇷 Especialista em Tributação Brasileira</p>
</div>
""", unsafe_allow_html=True)