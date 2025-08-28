# Development Environment Setup Guide

**Quick setup guide for the LangChain + Langfuse development environment in under 5 minutes.**

## 🎯 Overview

The Development Environment (`src/development/`) is optimized for:
- 🎛️ **Advanced Prompt Engineering**: Langfuse integration for prompt management
- 📊 **Comprehensive Observability**: Full request tracing and performance monitoring
- 🧪 **Experimental Features**: Testing new capabilities and configurations
- 🔍 **Debugging & Analysis**: Detailed token usage and cost tracking

## 🚀 Quick Setup

### 1. Prerequisites Check
```bash
# Verify Python version (3.9+ required)
python --version

# Check pip is available
pip --version

# Verify you have access to the project directory
ls -la src/development/
```

### 2. Install Dependencies
```bash
cd src/development
pip install -r requirements.txt
```

Expected output:
```
Successfully installed langchain-0.1.0 streamlit-1.29.0 langfuse-2.58.2 ...
```

### 3. Environment Configuration

Create your `.env` file:
```bash
cd src/development

# Create environment file
cat > .env << EOF
# OpenAI Configuration (Required)
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo
TEMPERATURE=0

# Database Configuration (Pre-configured for development)
DATABASE_URL=postgresql://postgres:XgfyZnwLEDuSDPAmMJchvdlpSKwpqRTb@maglev.proxy.rlwy.net:54891/railway

# Langfuse Configuration (Optional - for advanced features)
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_ENABLED=false

# Application Configuration
APP_TITLE=UberEats Brasil - Desenvolvimento
APP_ICON=🍔
LOG_LEVEL=INFO
EOF
```

### 4. Test Basic Setup
```bash
# Test database connectivity
python -c "from config.settings import get_dev_settings; s = get_dev_settings(); print(f'✅ Config loaded: {s.app_title}')"

# Test basic text-to-SQL functionality
python utils/test_simple_query.py
```

Expected output:
```
✅ Config loaded: UberEats Brasil - Desenvolvimento
✅ Basic text-to-SQL conversion working
✅ Database connection successful
✅ Query execution successful
```

### 5. Launch the Application
```bash
streamlit run apps/main_app.py
```

Expected output:
```
  You can now view your Streamlit app in your browser.
  
  Local URL: http://localhost:8501
  Network URL: http://192.168.1.100:8501
```

### 6. Verify Installation
1. Open http://localhost:8501 in your browser
2. You should see: "🍔 UberEats Brasil - Desenvolvimento"
3. Try a sample query: "Quantos pedidos temos no total?"
4. Verify you get SQL output and results

## 🎯 First Steps Tutorial

### Basic Query Testing
Try these queries to test your setup:

**1. Simple Count Query**
```
Input: "Quantos restaurantes temos cadastrados?"
Expected SQL: SELECT COUNT(*) FROM restaurants;
```

**2. Revenue Analysis**
```
Input: "Top 5 restaurantes por faturamento"
Expected SQL: SELECT name, SUM(total_amount) as revenue FROM restaurants r 
              JOIN invoices i ON r.cnpj = i.restaurant_key 
              GROUP BY name ORDER BY revenue DESC LIMIT 5;
```

**3. Regional Analysis**
```
Input: "Análise de pedidos por cidade"
Expected SQL: SELECT city, COUNT(*) as pedidos FROM restaurants r
              JOIN orders o ON r.cnpj = o.restaurant_key
              GROUP BY city ORDER BY pedidos DESC;
```

### Understanding the Interface

**Main Query Box**: Enter natural language questions in Portuguese
**SQL Output**: Generated SQL query appears here
**Results Table**: Query results displayed in tabular format
**Metrics Bar**: Shows tokens used, cost, and execution time
**Sidebar**: Configuration and connection status

## 🔧 Configuration Details

### Essential Settings

**OpenAI API Key** (Required)
- Get from: https://platform.openai.com/api-keys
- Format: `sk-proj-...` or `sk-...`
- Permissions: Read access to GPT models

**Database URL** (Pre-configured)
- Development database already set up
- Contains sample UberEats Brasil data
- Read-only access for safety

**Langfuse** (Optional)
- Enhanced prompt management
- Performance monitoring
- Can skip for basic usage

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | None | OpenAI API authentication |
| `OPENAI_MODEL` | No | gpt-3.5-turbo | AI model for SQL generation |
| `DATABASE_URL` | No | Pre-configured | PostgreSQL connection string |
| `LANGFUSE_ENABLED` | No | false | Enable advanced features |
| `LOG_LEVEL` | No | INFO | Logging verbosity |
| `APP_TITLE` | No | UberEats Brasil | Application title |

## 🎛️ Langfuse Integration (Advanced)

### Setup Langfuse
1. Create account at https://cloud.langfuse.com
2. Get your API keys from the settings page
3. Update your `.env` file:
```bash
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_ENABLED=true
```

### Langfuse Benefits
- **Prompt Management**: Version control for prompts
- **Performance Monitoring**: Token usage and cost tracking
- **A/B Testing**: Compare different prompt versions
- **Debugging**: Trace request flows and identify issues

## 🐛 Troubleshooting

### Common Setup Issues

**"OpenAI API key not found"**
```bash
# Check your .env file exists and has the key
cat .env | grep OPENAI_API_KEY

# Verify format (should start with sk-)
echo $OPENAI_API_KEY
```

**"Database connection failed"**
```bash
# Test connectivity
python -c "
from config.settings import get_dev_settings
import psycopg2
s = get_dev_settings()
conn = psycopg2.connect(s.database_url)
print('✅ Database connection successful')
conn.close()
"
```

**"Module not found errors"**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

**"Streamlit won't start"**
```bash
# Check port availability
lsof -i :8501

# Try alternative port
streamlit run apps/main_app.py --server.port 8502
```

### Performance Issues

**Slow query generation**
- Check internet connection (OpenAI API calls)
- Try simpler questions first
- Reduce temperature in settings

**Database timeouts**
- Large result sets may take time
- Try adding LIMIT to questions
- Check network connectivity

### Getting Help

**Check logs**
```bash
# View application logs
tail -f ../../ubereats_brasil.log

# Enable debug logging
export LOG_LEVEL=DEBUG
streamlit run apps/main_app.py
```

**Run diagnostics**
```bash
# Run comprehensive tests
python utils/test_simple_query.py
python utils/final_real_test.py

# Check configuration
python -c "
from config.settings import get_dev_settings
s = get_dev_settings()
print(f'OpenAI Key: {s.openai_api_key[:10]}...')
print(f'Database: {s.database_url.split('@')[1].split('/')[0]}')
print(f'Langfuse: {s.langfuse_enabled}')
"
```

## 🎯 Next Steps

### Basic Usage
1. **Learn the interface**: Try different query types
2. **Understand the data**: Explore available tables
3. **Practice queries**: Use the sample questions provided

### Advanced Features
1. **Set up Langfuse**: Follow the integration guide above
2. **Enable tracing**: Monitor performance and costs
3. **Customize prompts**: Improve query generation

### Development
1. **Explore the code**: Check `core/text_to_sql.py`
2. **Run tests**: Use utilities in `utils/`
3. **Add features**: Extend functionality

### Production Readiness
1. **Security review**: Check credential management
2. **Performance testing**: Run load tests
3. **Monitoring setup**: Configure observability

## 📚 Additional Resources

- **[Features Documentation](../DEVELOPMENT_FEATURES.md)** - Complete feature list
- **[API Reference](../api/DEVELOPMENT_API.md)** - Code documentation
- **[Architecture Guide](../architecture/SYSTEM_ARCHITECTURE.md)** - System design
- **[Production Guide](PRODUCTION_SETUP.md)** - Production deployment

## 🤝 Need Help?

**Common Questions**
- Check existing test files in `utils/` for examples
- Review configuration in `config/settings.py`
- Look at Streamlit app in `apps/main_app.py`

**Issues or Bugs**
- Check the logs first: `tail -f ../../ubereats_brasil.log`
- Run diagnostic scripts: `utils/test_*.py`
- Review your environment variables

**Feature Requests**
- Check if feature exists in production environment
- Look at advanced Langfuse features
- Consider extending the core text-to-SQL engine

---

**🚀 Ready to go?** Your development environment should now be fully functional. Try asking: "Quais são os restaurantes mais ativos de São Paulo?" and see the magic happen!