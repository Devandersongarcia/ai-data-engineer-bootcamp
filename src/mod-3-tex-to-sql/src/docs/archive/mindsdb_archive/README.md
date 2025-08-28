# Brasil Invoice Expert Chat - Structured Version

Uma aplicação Streamlit para interagir com o agente MindsDB especializado em análise tributária brasileira, agora com arquitetura estruturada e profissional.

## 📁 **Nova Estrutura de Diretórios**

```
src/mindsdb/
├── README.md                    # Documentação principal
├── requirements.txt             # Dependências Python
├── .env.example                 # Template de configuração
├── run_app.py                   # Script principal de execução
│
├── apps/                        # 🎯 Aplicações Streamlit
│   ├── __init__.py
│   └── chat_app.py              # Interface principal de chat
│
├── config/                      # ⚙️ Gerenciamento de configuração
│   ├── __init__.py
│   └── settings.py              # Configurações centralizadas
│
├── core/                        # 🧠 Lógica de negócio principal
│   ├── __init__.py
│   └── mindsdb_client.py        # Cliente MindsDB otimizado
│
├── utils/                       # 🛠️ Utilitários e helpers
│   ├── __init__.py
│   ├── logging_utils.py         # Sistema de logs padronizado
│   ├── metrics.py               # Métricas e monitoramento
│   └── token_manager.py         # Gerenciamento simples de tokens
│
├── sql/                         # 📊 Scripts e templates SQL
│   ├── setup_template.sql       # Template de setup seguro
│   └── test_queries.sql         # Consultas de teste
│
└── tests/                       # 🧪 Testes (para desenvolvimento futuro)
    └── __init__.py
```

## 🚀 **Como Executar**

### **Método 1: Script Principal (Recomendado)**
```bash
cd src/mindsdb
python run_app.py
```

### **Método 2: Streamlit Direto**
```bash
cd src/mindsdb
PYTHONPATH=. streamlit run apps/chat_app.py --server.port 8502
```

### **Método 3: Usando o comando original**
```bash
PYTHONPATH=src/mindsdb streamlit run src/mindsdb/apps/chat_app.py --server.port 8502
```

## 🏗️ **Melhorias da Nova Arquitetura**

### **1. Separação de Responsabilidades**
- **`apps/`** - Interface do usuário (Streamlit)
- **`core/`** - Lógica de negócio principal
- **`config/`** - Gerenciamento de configurações
- **`utils/`** - Funções auxiliares reutilizáveis

### **2. Imports Estruturados**
```python
# Antes (problemático)
from mindsdb_sdk_wrapper import connect
from config import config

# Agora (estruturado)
from core.mindsdb_client import connect
from config.settings import get_settings
from utils.logging_utils import get_logger
```

### **3. Configuração Profissional**
- **Singleton pattern** para configurações
- **Validação automática** de variáveis de ambiente
- **Configurações específicas** por módulo

### **4. Logging Padronizado**
- **Context managers** para performance
- **Mascaramento automático** de informações sensíveis
- **Logs estruturados** com níveis apropriados

## 📋 **Setup Rápido**

1. **Configure o ambiente:**
   ```bash
   cp .env.example .env
   # Edite .env com suas credenciais
   ```

2. **Configure MindsDB:**
   ```bash
   # Use sql/setup_template.sql como base
   # Substitua placeholders pelas credenciais reais
   ```

3. **Execute a aplicação:**
   ```bash
   python run_app.py
   ```

## 🔄 **Migração dos Arquivos Antigos**

A estruturação moveu os arquivos conforme:

| **Arquivo Original** | **Nova Localização** | **Status** |
|---------------------|---------------------|------------|
| `chat_app_improved.py` | `apps/chat_app.py` | ✅ Migrado |
| `config.py` | `config/settings.py` | ✅ Melhorado |
| `mindsdb_sdk_wrapper.py` | `core/mindsdb_client.py` | ✅ Otimizado |
| `utils.py` | `utils/metrics.py` | ✅ Expandido |
| `setup_secure.sql` | `sql/setup_template.sql` | ✅ Movido |
| `queries.sql` | `sql/test_queries.sql` | ✅ Movido |

## 🧪 **Testando a Nova Estrutura**

1. **Teste básico de imports:**
   ```python
   from config.settings import get_settings
   from core.mindsdb_client import connect
   from utils.logging_utils import get_logger
   ```

2. **Teste de configuração:**
   ```python
   settings = get_settings()
   print(settings.mindsdb_server_url)
   ```

3. **Teste de conexão:**
   ```python
   server = connect("http://127.0.0.1:47334")
   print("✅ Conexão funcionando!")
   ```

## 🎯 **Próximos Passos**

- **Testes automatizados** na pasta `tests/`
- **Múltiplas aplicações** na pasta `apps/`
- **Configurações específicas** por ambiente
- **Deploy em containers** com estrutura profissional

## 📦 **Compatibilidade**

- ✅ **Mantém funcionalidade** original intacta
- ✅ **Melhora organização** de código
- ✅ **Facilita manutenção** e extensão
- ✅ **Segue padrões** Python profissionais

---

**🧠 Brasil Invoice Expert** - Agora com arquitetura profissional! 🇧🇷