# 🆘 Troubleshooting Guide

## Common Issues & Solutions

### 1. Import Errors

#### Problem: `ModuleNotFoundError: No module named 'core'`
```
File "apps/main_app.py", line 11, in <module>
    from core.vanna_converter import VannaTextToSQLConverter
ModuleNotFoundError: No module named 'core'
```

**Solution:** Always run applications from the `src/production/` directory:
```bash
# ✅ Correct - from production directory
cd /path/to/langchain_text_query/src/production
streamlit run apps/main_app.py --server.port 8501

# ❌ Wrong - from apps directory
cd /path/to/langchain_text_query/src/production/apps
streamlit run main_app.py  # This will fail
```

#### Problem: `ModuleNotFoundError: No module named 'config'` or `utils`
**Solution:** Same as above - ensure you're in the `production/` directory.

### 2. Database Connection Issues

#### Problem: `Database connection failed: connection refused`
**Solutions:**
1. Check your `.env` file exists and has correct `DATABASE_URL`
2. Test connection manually:
   ```bash
   python -c "
   from config.settings import get_settings
   print(get_settings().database_url)
   "
   ```
3. Verify network access to database host
4. Check if database is running

#### Problem: `relation "extracted_invoices" does not exist`
**Solution:** The table name has been corrected to `ubears_invoices_extract_airflow`. This should be automatic, but if you see this error:
1. Clear ChromaDB cache: `rm -rf data/chromadb/chroma.sqlite3`
2. Restart the application

### 3. OpenAI API Issues

#### Problem: `OpenAI API error: Invalid API key`
**Solutions:**
1. Check your `.env` file has the correct `OPENAI_API_KEY`
2. Verify the key is valid at https://platform.openai.com
3. Ensure you have API credits available

#### Problem: `OpenAI API error: Rate limit exceeded`
**Solutions:**
1. Wait a moment and try again
2. Check your OpenAI usage limits
3. Consider upgrading your OpenAI plan

### 4. ChromaDB Issues

#### Problem: `Permission denied: data/chromadb`
**Solutions:**
```bash
# Fix permissions
chmod -R 755 data/chromadb

# Or recreate the directory
rm -rf data/chromadb
mkdir -p data/chromadb
```

#### Problem: ChromaDB telemetry warnings/errors
These warnings are harmless:
```
Failed to send telemetry event: capture() takes 1 positional argument but 3 were given
```
**Solution:** Already disabled in code, warnings can be ignored.

### 5. Performance Issues

#### Problem: Queries taking longer than 5 seconds
**Solutions:**
1. Check if connection pooling is active:
   ```python
   from utils.connection_pool import get_connection_manager
   print(get_connection_manager().get_all_pool_status())
   ```
2. Enable query caching in your requests
3. Check network latency to database
4. Monitor with: `ENABLE_PERFORMANCE_TRACKING=true`

#### Problem: Memory usage growing over time
**Solutions:**
1. Restart the application periodically
2. Clear query cache: `rm -rf data/chromadb/chroma.sqlite3`
3. Monitor cache size in logs

### 6. Streamlit Issues

#### Problem: `Session state does not function when running a script without streamlit run`
**Solution:** Always use `streamlit run` command, never `python` directly:
```bash
# ✅ Correct
streamlit run apps/main_app.py --server.port 8501

# ❌ Wrong  
python apps/main_app.py
```

#### Problem: Streamlit app doesn't update when code changes
**Solutions:**
1. Enable auto-rerun in Streamlit settings
2. Install watchdog: `pip install watchdog`
3. Manually refresh the browser page

### 7. Query Issues

#### Problem: "Pergunta muito vaga ou complexa" error
**Solutions:**
1. Try simpler queries first: "me mostre as notas"
2. Add more specific details: "faturamento dos últimos 7 dias"
3. Check if the query pattern is supported

#### Problem: No data returned (empty DataFrame)
**Solutions:**
1. Verify table has data:
   ```python
   from sqlalchemy import create_engine, text
   from config.settings import get_settings
   engine = create_engine(get_settings().database_url)
   with engine.connect() as conn:
       result = conn.execute(text("SELECT COUNT(*) FROM ubears_invoices_extract_airflow"))
       print(f"Table has {result.fetchone()[0]} rows")
   ```
2. Check query logic and date filters
3. Review generated SQL in logs

### 8. Environment Issues

#### Problem: Environment variables not loading
**Solutions:**
1. Check `.env` file exists in `src/production/` directory
2. Verify `.env` file format (no spaces around `=`):
   ```bash
   OPENAI_API_KEY=your_key_here
   # Not: OPENAI_API_KEY = your_key_here
   ```
3. Check if `.env` is in `.gitignore` (should be)

#### Problem: `python-dotenv` not found
**Solution:** Install missing dependencies:
```bash
pip install -r requirements.txt
```

### 9. Port Issues

#### Problem: `Address already in use: 8501`
**Solutions:**
1. Use a different port:
   ```bash
   streamlit run apps/main_app.py --server.port 8502
   ```
2. Kill process using the port:
   ```bash
   lsof -ti:8501 | xargs kill -9
   ```
3. Find and stop other Streamlit processes

### 10. Logging Issues

#### Problem: No logs appearing or log files not created
**Solutions:**
1. Check log file paths in `config/settings.py`
2. Ensure directory permissions for log files
3. Check `LOG_LEVEL` environment variable
4. Verify logging is enabled: `ENABLE_PERFORMANCE_TRACKING=true`

## 🔍 Debugging Steps

### Quick Health Check
```bash
cd /path/to/langchain_text_query/src/production
python tests/test_phase3_compatibility.py
```
Expected: All tests pass ✅

### Verify Configuration
```bash
python -c "
from config.settings import get_settings
settings = get_settings()
print(f'DB: {settings.database_url[:50]}...')
print(f'OpenAI: {\"✅\" if settings.openai_api_key else \"❌ Missing\"}')
print(f'ChromaDB: {settings.chroma_path}')
"
```

### Test Database Connection
```bash
python -c "
from sqlalchemy import create_engine, text
from config.settings import get_settings
try:
    engine = create_engine(get_settings().database_url)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM ubears_invoices_extract_airflow'))
        count = result.fetchone()[0]
    print(f'✅ Database connected: {count} invoices found')
except Exception as e:
    print(f'❌ Database error: {e}')
"
```

### Test Core Functionality
```bash
python -c "
from core.vanna_converter import VannaTextToSQLConverter
try:
    converter = VannaTextToSQLConverter()
    result = converter.process_question('me mostre as notas')
    print(f'✅ Core working: {len(result[\"result\"])} rows returned')
except Exception as e:
    print(f'❌ Core error: {e}')
"
```

## 📞 Getting Help

### Log Files to Check
1. Application logs: `../../ubereats_brasil_vanna.log`
2. System logs: Check terminal output
3. Streamlit logs: Browser developer console

### Information to Provide
When reporting issues, include:
1. Operating system and Python version
2. Full error message and stack trace
3. Content of `.env` file (without API keys)
4. Steps to reproduce the issue
5. Output of health check commands above

### Performance Monitoring
```bash
# Check connection pool status
python -c "
from utils.connection_pool import get_connection_manager
manager = get_connection_manager()
import json
print(json.dumps(manager.get_all_pool_status(), indent=2))
"

# Check cache performance
python -c "
from utils.performance_utils import get_performance_monitor
monitor = get_performance_monitor()
metrics = monitor.get_metrics()
print(f'Cache hits: {metrics.get(\"cache_hits\", 0)}')
print(f'Cache misses: {metrics.get(\"cache_misses\", 0)}')
"
```

---

*If issues persist, check the main [README.md](README.md) for architecture details or [SETUP.md](SETUP.md) for configuration help.*