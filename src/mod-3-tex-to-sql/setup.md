# 🔒 Security Setup Guide

## ⚠️ CRITICAL: Environment Variables Setup

This project has been updated to remove all hardcoded credentials. **You must set up environment variables before running the application**.

### Required Environment Variables

#### For Development (`src/development/`)
```bash
# Copy the template and fill in your values
cp src/development/.env.example src/development/.env

# Edit the .env file with your actual credentials
```

#### For Production (`src/production/`)
```bash
# Copy the template and fill in your values
cp src/production/.env.example src/production/.env

# Edit the .env file with your actual credentials
```

#### For MindsDB (`src/mindsdb/`)
```bash
# Copy the template and fill in your values
cp src/mindsdb/.env.example src/mindsdb/.env

# Edit the .env file with your actual credentials
```

### Environment Variables Required

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-proj-...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:port/db` |
| `QDRANT_URL` | Qdrant vector database URL | `https://your-cluster.qdrant.io:6333` |
| `QDRANT_API_KEY` | Qdrant API key | `your-qdrant-api-key` |

### Security Improvements Made

✅ **Removed hardcoded API keys** from all source files
✅ **Removed hardcoded database credentials** from configuration files
✅ **Added environment variable validation** at startup
✅ **Created .env.example templates** for each module
✅ **Updated SQL setup files** to use environment variables

### Before Running the Application

1. **Set up environment variables** using the templates provided
2. **Verify all required variables are set**:
   ```bash
   # Check if variables are set
   echo $OPENAI_API_KEY
   echo $DATABASE_URL
   ```
3. **The application will fail with clear error messages** if required variables are missing

### Security Best Practices

- ✅ **Never commit `.env` files** to version control
- ✅ **Use different API keys** for development and production
- ✅ **Rotate API keys regularly**
- ✅ **Use strong database passwords**
- ✅ **Limit database user permissions** to only what's needed

### Git Security

Add to your `.gitignore`:
```
# Environment variables
.env
*.env
!.env.example
```

## 🚨 If You Previously Had This Code

**IMPORTANT**: If you previously cloned this repository:

1. **The exposed API keys have been removed** - you need to set up your own
2. **Check your git history** - consider rebasing to remove old credentials
3. **Revoke any exposed API keys** and generate new ones
4. **Update your deployment environments** with new credentials

## Need Help?

If you encounter issues:
1. Check that all required environment variables are set
2. Verify your API keys are valid and have proper permissions
3. Ensure database connectivity from your environment
4. Check the application logs for specific error messages