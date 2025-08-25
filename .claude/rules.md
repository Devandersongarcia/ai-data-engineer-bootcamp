# Development Rules

## Python
- **Python 3.11+** with type hints
- **Pydantic** for data validation
- **Docstrings only** - NO inline comments ever
- **Structure**: `dags/` | `include/` | `config/` | `tests/`

## Airflow
- TaskFlow API (`@task` decorators)
- Idempotent tasks with retries
- Credentials in Connections, not code
- Business logic in YAML configs

## LLM/OpenAI
- Temperature ≤ 0.3
- Structured output (JSON mode)
- Retry with exponential backoff
- External prompt storage
- Monitor token costs

## Database
- Connection pooling
- Transactions with rollback
- Audit columns (`created_at`, `updated_at`)
- Proper indexes

## Docker
- Multi-stage builds
- Pin all versions
- Health checks
- Use `.env` files

## Testing
- 80% minimum coverage
- Mock external APIs
- Use pytest

## Security
- No secrets in code
- Environment variables only
- Encrypt sensitive data
- Audit all access

## Quality Checklist

✅ **DO**
- Single responsibility
- Error handling
- Type hints
- Small functions (<50 lines)
- Test coverage
- Code review

❌ **DON'T**
- Write inline comments (use docstrings)
- Hardcode credentials
- Use `print()` over logging
- Skip error handling
- Mix business/infrastructure
- Create god functions
- Ignore type hints