"""
Constants for the MindsDB Chat Application
Centralized location for all hardcoded strings and configuration values
"""

# UI Text Constants - Portuguese
class UIText:
    # Main Headers
    MINDSDB_CONNECTION_HEADER = "🔌 Conexão MindsDB"
    CHAT_SUBTITLE = "Chat direto com seu agente MindsDB"
    QUICK_SETUP_HEADER = "🚀 Setup Rápido"
    STATISTICS_HEADER = "📊 Estatísticas"
    
    # Form Labels
    MINDSDB_SERVER_URL_LABEL = "MindsDB Server URL"
    AGENT_NAME_LABEL = "Nome do Agente"
    MINDSDB_SERVER_HELP = "URL do servidor MindsDB"
    AGENT_NAME_HELP = "Selecione o agente MindsDB especializado"
    
    # Agent Selection
    LOADING_AGENTS_MESSAGE = "🔄 Carregando agentes disponíveis..."
    NO_AGENTS_FOUND_MESSAGE = "❌ Nenhum agente encontrado"
    REFRESH_AGENTS_BUTTON = "🔄 Atualizar Lista"
    AGENT_SELECTION_PLACEHOLDER = "Selecione um agente..."
    CONNECTION_REQUIRED_MESSAGE = "⚠️ Conecte ao servidor primeiro para ver agentes"
    
    # Agent Descriptions (for your multi-agent setup)
    AGENT_DESCRIPTIONS = {
        "agent_postgres_transactions": "🏦 PostgreSQL - Dados transacionais, invoices, pagamentos, compliance fiscal",
        "agent_mongo_catalog": "🍽️ MongoDB - Restaurantes e cardápios (queries simples, sem joins complexos)", 
        "agent_supabase_realtime": "📡 Supabase - Dados tempo real, status de pedidos, tracking, operações ativas",
        "agent_ubereats_coordinator": "🎯 Coordenador Master - Análise completa cross-database, BI integrado",
        "brasil_invoice_expert": "📊 Expert fiscal brasileiro - Análise de notas fiscais e tributação"
    }
    
    # Buttons
    CONNECT_BUTTON = "🔗 Conectar"
    DISCONNECT_BUTTON = "🔌 Desconectar"
    CLEAR_CHAT_BUTTON = "🗑️ Limpar Chat"
    STATUS_BUTTON = "📊 Status"
    
    # Quick Questions
    QUICK_QUESTIONS_HEADER = "🚀 Perguntas Rápidas:"
    SUMMARY_BUTTON = "📈 Resumo"
    TOP5_BUTTON = "🏆 Top 5"
    STATES_BUTTON = "🗺️ Estados"
    
    # Status Messages
    CONNECTED_STATUS = "🟢 Conectado"
    DISCONNECTED_STATUS = "🔴 Desconectado"
    THINKING_STATUS = "🧠 Pensando..."
    
    # Success Messages
    CONNECTION_SUCCESS = "✅ Conectado ao agente '{}'!"
    READY_MESSAGE = "🎉 Pronto para conversar!"
    SERVER_REACHED = "✅ Servidor alcançado!"
    AGENT_FOUND = "✅ Agente encontrado!"
    CONNECTION_COMPLETE = "Conectado com sucesso!"
    CHAT_CLEARED = "✅ Chat limpo! Problema de tokens resolvido."
    
    # Error Messages
    CONNECTION_ERROR_PREFIX = "🔌 Erro de conexão: {}"
    AGENT_ERROR_PREFIX = "🤖 Erro do agente: {}"
    UNEXPECTED_ERROR_PREFIX = "❌ {}"
    EMPTY_RESPONSE = "❌ Agente retornou resposta vazia"
    
    # Warning Messages
    LONG_QUESTION_WARNING = "⚠️ Pergunta muito longa foi truncada para caber no limite de tokens."
    HIGH_TOKEN_WARNING = "⚠️ Uso de tokens alto. Chat será otimizado automaticamente."
    
    # Connection Instructions
    SERVER_UNREACHABLE_HELP = """
    **Servidor MindsDB inacessível:**
    1. ✅ Verifique se MindsDB está rodando
    2. 🌐 Confirme a URL do servidor
    3. 🔥 Tente: `python -m mindsdb` para iniciar localmente
    """
    
    AGENT_NOT_FOUND_HELP = """
    **Agente não encontrado:**
    1. 📋 Execute `SHOW AGENTS;` no MindsDB Editor
    2. 🛠️ Se não existir, execute o arquivo SQL de setup
    3. 🔗 MindsDB Editor: http://127.0.0.1:47334
    """
    
    # Input Placeholders
    CHAT_INPUT_PLACEHOLDER = "Digite sua pergunta sobre notas fiscais..."
    
    # Metrics Labels
    QUERIES_METRIC = "Consultas"
    SUCCESS_METRIC = "Sucessos"
    SUCCESS_RATE_METRIC = "Taxa Sucesso"
    AVG_TIME_METRIC = "Tempo Médio"
    SESSION_LABEL = "Sessão: {}"
    TOKENS_LABEL = "Tokens: {}/{} ({:.1f}%)"
    
    # Footer
    FOOTER_TEXT = "{} {} | MindsDB Python SDK | 🇧🇷 Especialista em Tributação Brasileira"


# Quick Questions Templates
class QuickQuestions:
    GENERAL_SUMMARY = "Me dê um resumo geral dos dados"
    TOP5_RESTAURANTS = "Top 5 restaurantes por faturamento"
    STATES_ANALYSIS = "Análise por estado brasileiro"
    PAYMENT_METHODS = "Métodos de pagamento mais usados"
    AVERAGE_TICKET = "Ticket médio por região"
    TAX_COMPLIANCE = "Como funciona tributação delivery Brasil?"


# API and Connection Constants
class APIConstants:
    DEFAULT_TIMEOUT = 60
    DEFAULT_CONNECTION_TIMEOUT = 30
    DEFAULT_MAX_RETRIES = 3
    SQL_QUERY_ENDPOINT = "/api/sql/query"
    STATUS_ENDPOINT = "/api/status"
    
    # Retry Configuration
    RETRY_BACKOFF_FACTOR = 2.0  # Exponential backoff multiplier
    RETRY_INITIAL_DELAY = 1.0   # Initial delay in seconds
    RETRY_MAX_DELAY = 30.0      # Maximum delay between retries
    RETRYABLE_HTTP_CODES = [408, 429, 502, 503, 504]  # HTTP codes to retry
    RETRYABLE_EXCEPTIONS = [
        "ConnectionError", "Timeout", "ConnectTimeout", 
        "ReadTimeout", "HTTPError"
    ]
    
    # SQL Query Templates
    AGENT_QUERY_TEMPLATE = """
    SELECT answer 
    FROM mindsdb.{agent_name} 
    WHERE question = '{question}'
    """
    
    SHOW_AGENTS_QUERY = "SHOW AGENTS"


# Error Messages and Validation
class ErrorMessages:
    REQUIRED_SERVER_URL = "URL do servidor é obrigatória"
    REQUIRED_AGENT_NAME = "Nome do agente é obrigatório"
    INVALID_URL_FORMAT = "URL deve começar com http:// ou https://"
    AGENT_NAME_TOO_LONG = "Nome do agente muito longo (máximo 50 caracteres)"
    
    # Formatted error messages
    TIMEOUT_ERROR = "⏱️ Tempo limite excedido. Tente uma pergunta mais simples."
    CONNECTION_ERROR = "🔌 Problema de conexão com o servidor MindsDB."
    AGENT_NOT_FOUND_ERROR = "🤖 Agente não encontrado. Verifique se foi criado corretamente."
    UNAUTHORIZED_ERROR = "🔑 Erro de autenticação. Verifique suas credenciais."
    RATE_LIMIT_ERROR = "🚦 Limite de requisições atingido. Aguarde um momento."
    GENERIC_ERROR = "❌ Erro: {}"


# Application Configuration
class AppConfig:
    MAX_CHAT_HISTORY = 50
    MAX_CONVERSATION_LENGTH = 10
    MAX_QUESTION_TOKENS = 1000
    MAX_TEXT_CHARS = 4000
    TOKEN_WARNING_THRESHOLD = 80
    
    # Performance tracking
    SLIDING_WINDOW_SIZE = 10
    
    # Security
    MAX_AGENT_NAME_LENGTH = 50
    
    # Retry and resilience
    ENABLE_RETRY_FEEDBACK = True  # Show retry status to users
    RETRY_STATUS_MESSAGES = True  # Display retry attempts
    
    # Connection pooling
    CONNECTION_POOL_SIZE = 10      # Maximum connections per pool
    CONNECTION_POOL_MAXSIZE = 20   # Maximum total connections
    CONNECTION_POOL_BLOCK = False  # Don't block when pool exhausted
    CONNECTION_KEEP_ALIVE = 300    # Keep connections alive for 5 minutes


# Feature Descriptions for Welcome Screen
class FeatureDescriptions:
    FINANCIAL_ANALYSIS = """
    - **📊 Análise Financeira**
      - "Qual o faturamento total por estado?"
      - "Top 5 restaurantes por receita"
      - "Ticket médio por região"
    """
    
    RESTAURANT_DATA = """
    - **🏪 Dados de Restaurantes**  
      - "Quantos restaurantes únicos temos?"
      - "Restaurantes mais ativos por cidade"
      - "Análise de performance por estabelecimento"
    """
    
    PAYMENT_ANALYSIS = """
    - **💳 Análise de Pagamentos**
      - "Métodos de pagamento mais usados"
      - "Gorjetas médias por tipo de pagamento"
      - "Tendências de pagamento por região"
    """
    
    USAGE_INSTRUCTIONS = """
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
    """