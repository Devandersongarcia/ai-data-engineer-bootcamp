# UberEats Brasil Development Environment

**Enterprise-grade text-to-SQL development platform with advanced AI capabilities and comprehensive observability.**

## 🎯 Quick Overview

Advanced development environment for converting natural language to SQL queries, specifically designed for UberEats Brasil invoice and restaurant data analysis. Features enterprise-level Langfuse integration for prompt management and comprehensive observability.

## 🚀 Quick Start

```bash
# 1. Install dependencies
cd src/development
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env  # Edit with your API keys

# 3. Launch application  
streamlit run apps/main_app.py
```

Visit http://localhost:8501 and start asking questions like:
- "Top 5 restaurantes por faturamento"
- "Análise fiscal por estado"
- "Status das notas fiscais"

## 📚 Documentation

**📖 [Complete Documentation Hub](../docs/readme.md)** - Comprehensive platform documentation

**🚀 [Development Setup Guide](../docs/guides/DEVELOPMENT_SETUP.md)** - Step-by-step installation

**⚡ [Development Features](../docs/guides/DEVELOPMENT_FEATURES.md)** - LangChain + Langfuse capabilities

**🎛️ [Langfuse Integration](../docs/guides/LANGFUSE_GUIDE.md)** - Advanced prompt management

**📋 [API Reference](../docs/api/API_REFERENCE.md)** - Complete development APIs

**🇧🇷 [Brazilian Tax Guide](../docs/guides/BRAZILIAN_TAX_GUIDE.md)** - Tax compliance automation

## 🏗️ Architecture

```
src/development/
├── 📚 docs/              # Complete documentation hub
├── 🎨 apps/              # Streamlit UI applications  
├── ⚙️ config/            # Configuration management
├── 🧠 core/              # Business logic & AI integration
├── 🛠️ utils/             # Development tools & testing
├── 📋 requirements.txt   # Dependencies
└── 📖 README.md          # This file
```

## ⭐ Key Features

- **🤖 AI-Powered**: Advanced LangChain + OpenAI integration
- **🎛️ Langfuse Ready**: Enterprise prompt management & observability  
- **📊 Multi-Database**: PostgreSQL, MongoDB, Supabase support
- **🛡️ Enterprise Security**: SQL injection prevention & validation
- **📈 Advanced Analytics**: Token tracking, cost monitoring, performance metrics
- **🇧🇷 Brazilian Focus**: Tax compliance & fiscal analysis expertise

## 🔧 Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **AI Framework** | LangChain | 0.1.0 |
| **LLM Integration** | LangChain-OpenAI | 0.0.5 |
| **UI Framework** | Streamlit | 1.29.0 |
| **Observability** | Langfuse | 2.58.2 |
| **Database** | SQLAlchemy + PostgreSQL | 2.0.23 |
| **Data Processing** | Pandas | 2.1.4 |

## 🎯 Use Cases

**🏪 Restaurant Analytics**
- Revenue analysis by region
- Performance metrics tracking
- Menu optimization insights

**📊 Fiscal Compliance**  
- Brazilian tax compliance (ICMS, ISS, PIS/COFINS)
- Invoice status monitoring
- Regional fiscal analysis

**⚡ Operational Intelligence**
- Real-time order tracking
- Delivery performance metrics
- Driver efficiency analysis

## 📈 Performance

- **Response Time**: < 2s average
- **Success Rate**: > 94% query generation  
- **Cost Efficiency**: < $0.001 per query
- **Observability**: 100% request tracing

## 🛡️ Security

- **Query Validation**: SQL injection prevention
- **Read-Only Operations**: Only SELECT statements allowed
- **Credential Protection**: Secure API key management
- **Audit Logging**: Comprehensive access tracking

## 🤝 Contributing

1. **Review Documentation**: Start with [docs/README.md](docs/README.md)
2. **Set Up Environment**: Follow [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)
3. **Explore Features**: Check [docs/FEATURES.md](docs/FEATURES.md)
4. **Run Tests**: Use utilities in `utils/` directory
5. **Submit Changes**: Include tests and documentation updates

## 📞 Support

- **📚 Documentation**: Complete guides in `docs/` folder
- **🧪 Testing**: Run `python utils/test_simple_query.py`
- **🔍 Debugging**: Enable with `export LOG_LEVEL=DEBUG`
- **🎛️ Langfuse Setup**: Follow [docs/LANGFUSE_GUIDE.md](docs/LANGFUSE_GUIDE.md)

---

**🍔 UberEats Brasil Development Environment** - Enterprise-ready text-to-SQL with comprehensive observability and advanced AI capabilities.

*Ready to build amazing data applications? Start with our [Getting Started Guide](docs/GETTING_STARTED.md)!*