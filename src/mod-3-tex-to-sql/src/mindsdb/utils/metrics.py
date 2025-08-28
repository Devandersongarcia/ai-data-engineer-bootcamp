"""
Utility functions for MindsDB Chat App
Includes metrics tracking, error handling, and helper functions
"""
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import streamlit as st

# Import constants for error messages
try:
    from config.constants import ErrorMessages
except ImportError:
    # Fallback if constants not available
    class ErrorMessages:
        TIMEOUT_ERROR = "⏱️ Tempo limite excedido. Tente uma pergunta mais simples."
        CONNECTION_ERROR = "🔌 Problema de conexão com o servidor MindsDB."
        AGENT_NOT_FOUND_ERROR = "🤖 Agente não encontrado. Verifique se foi criado corretamente."
        UNAUTHORIZED_ERROR = "🔑 Erro de autenticação. Verifique suas credenciais."
        RATE_LIMIT_ERROR = "🚦 Limite de requisições atingido. Aguarde um momento."
        GENERIC_ERROR = "❌ Erro: {}"

logger = logging.getLogger(__name__)

class ChatMetrics:
    """Simple metrics tracking for chat interactions"""
    
    def __init__(self):
        if "metrics" not in st.session_state:
            st.session_state.metrics = {
                "total_queries": 0,
                "successful_queries": 0,
                "failed_queries": 0,
                "average_response_time": 0.0,
                "session_start": datetime.now(),
                "last_query_time": None,
                "response_times": []
            }
    
    def start_query(self) -> float:
        """Start timing a query"""
        return time.time()
    
    def end_query(self, start_time: float, success: bool = True) -> float:
        """End timing a query and update metrics"""
        response_time = time.time() - start_time
        
        metrics = st.session_state.metrics
        metrics["total_queries"] += 1
        metrics["last_query_time"] = datetime.now()
        metrics["response_times"].append(response_time)
        
        if success:
            metrics["successful_queries"] += 1
        else:
            metrics["failed_queries"] += 1
        
        # Update average response time (sliding window of last 10)
        recent_times = metrics["response_times"][-10:]
        metrics["average_response_time"] = sum(recent_times) / len(recent_times)
        
        return response_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current metrics"""
        metrics = st.session_state.metrics
        session_duration = datetime.now() - metrics["session_start"]
        
        return {
            "total_queries": metrics["total_queries"],
            "successful_queries": metrics["successful_queries"], 
            "failed_queries": metrics["failed_queries"],
            "success_rate": (metrics["successful_queries"] / max(metrics["total_queries"], 1)) * 100,
            "average_response_time": metrics["average_response_time"],
            "session_duration": str(session_duration).split('.')[0],  # Remove microseconds
            "last_query": metrics["last_query_time"].strftime("%H:%M:%S") if metrics["last_query_time"] else "Nunca"
        }

def format_error_message(error: Exception) -> str:
    """Format error messages for better user experience"""
    error_str = str(error).lower()
    
    if "timeout" in error_str:
        return ErrorMessages.TIMEOUT_ERROR
    elif "connection" in error_str or "unreachable" in error_str:
        return ErrorMessages.CONNECTION_ERROR
    elif "not found" in error_str and "agent" in error_str:
        return ErrorMessages.AGENT_NOT_FOUND_ERROR
    elif "unauthorized" in error_str or "forbidden" in error_str:
        return ErrorMessages.UNAUTHORIZED_ERROR
    elif "rate limit" in error_str:
        return ErrorMessages.RATE_LIMIT_ERROR
    else:
        return ErrorMessages.GENERIC_ERROR.format(str(error))

def validate_connection_inputs(server_url: str, agent_name: str) -> Optional[str]:
    """Validate connection inputs"""
    try:
        from config.constants import ErrorMessages, AppConfig
        
        if not server_url or not server_url.strip():
            return ErrorMessages.REQUIRED_SERVER_URL
        
        if not agent_name or not agent_name.strip():
            return ErrorMessages.REQUIRED_AGENT_NAME
        
        if not server_url.startswith(('http://', 'https://')):
            return ErrorMessages.INVALID_URL_FORMAT
        
        if len(agent_name) > AppConfig.MAX_AGENT_NAME_LENGTH:
            return ErrorMessages.AGENT_NAME_TOO_LONG
        
        return None
    except ImportError:
        # Fallback to hardcoded values if constants not available
        if not server_url or not server_url.strip():
            return "URL do servidor é obrigatória"
        
        if not agent_name or not agent_name.strip():
            return "Nome do agente é obrigatório"
        
        if not server_url.startswith(('http://', 'https://')):
            return "URL deve começar com http:// ou https://"
        
        if len(agent_name) > 50:
            return "Nome do agente muito longo (máximo 50 caracteres)"
        
        return None

def show_connection_status(is_connected: bool, agent_name: str = "", server_url: str = "") -> None:
    """Show connection status in sidebar"""
    if is_connected:
        st.sidebar.success("🟢 Conectado")
        st.sidebar.text(f"Agente: {agent_name}")
        if server_url:
            st.sidebar.text(f"Servidor: {server_url}")
    else:
        st.sidebar.error("🔴 Desconectado")

def show_metrics_sidebar(metrics: ChatMetrics) -> None:
    """Show performance metrics in sidebar"""
    with st.sidebar.expander("📊 Estatísticas"):
        stats = metrics.get_stats()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Consultas", stats["total_queries"])
            st.metric("Sucessos", stats["successful_queries"])
        
        with col2:
            st.metric("Taxa Sucesso", f"{stats['success_rate']:.1f}%")
            st.metric("Tempo Médio", f"{stats['average_response_time']:.1f}s")
        
        st.text(f"Sessão: {stats['session_duration']}")
        st.text(f"Última: {stats['last_query']}")

def create_quick_questions() -> List[str]:
    """Create predefined quick questions"""
    return [
        "Me dê um resumo geral dos dados",
        "Top 5 restaurantes por faturamento", 
        "Análise por estado brasileiro",
        "Métodos de pagamento mais usados",
        "Ticket médio por região",
        "Como funciona tributação delivery Brasil?"
    ]

def log_user_interaction(question: str, response: str, response_time: float, success: bool) -> None:
    """Log user interactions for analysis"""
    logger.info(
        f"User interaction - "
        f"Question: {question[:50]}{'...' if len(question) > 50 else ''} | "
        f"Response length: {len(response)} chars | "
        f"Time: {response_time:.2f}s | "
        f"Success: {success}"
    )

def truncate_message_history(messages: List[Dict[str, str]], max_length: int = 50) -> List[Dict[str, str]]:
    """Truncate message history to prevent memory issues"""
    if len(messages) > max_length:
        # Keep first message (often contains important context) and recent messages
        return [messages[0]] + messages[-(max_length-1):]
    return messages

def format_response_for_display(response: str) -> str:
    """Format agent response for better display"""
    # Clean up common formatting issues
    response = response.replace("\\n", "\n")
    response = response.replace("```sql", "\n```sql")
    response = response.replace("```", "\n```\n")
    
    # Add line breaks for better readability
    if "SELECT" in response.upper() and "```" not in response:
        response = f"```sql\n{response}\n```"
    
    return response.strip()