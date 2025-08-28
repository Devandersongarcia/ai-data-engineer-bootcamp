"""Script to migrate existing prompts to Langfuse."""

import os
import sys
from dotenv import load_dotenv

# Add the parent directories to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings
from core.langfuse_service import LangfuseService, PromptTemplate

# Load environment variables
load_dotenv()


def create_sql_prompts(langfuse_service: LangfuseService) -> bool:
    """Create SQL-related prompts in Langfuse."""
    
    # System message prompt
    system_prompt = PromptTemplate(
        name="sql_system_message",
        content="You are a helpful SQL assistant that only generates SELECT queries.",
        variables=[],
        labels=["production", "development"],
        config={
            "type": "system",
            "model": "gpt-3.5-turbo",
            "temperature": 0
        }
    )
    
    # Main SQL generation prompt
    sql_prompt = PromptTemplate(
        name="sql_generation_template", 
        content="""
You are a SQL expert. Convert the following natural language question into a SQL SELECT query.

Database Schema:
{schema}

CRITICAL RULES:
1. ALWAYS use extracted_invoices table for invoice queries - it has complete data (41 records)
2. NEVER use invoices table - it only has basic data (3 records)
3. extracted_invoices has proper DATE/TIMESTAMP fields: invoice_date, created_at, extracted_at
4. Use extracted_invoices.created_at for recent date queries: >= CURRENT_DATE - INTERVAL '7 days'

MANDATORY Table Selection:
- For ANY invoice query → USE extracted_invoices table
- For date/time queries → USE extracted_invoices.created_at or invoice_date
- For vendor/restaurant queries → USE extracted_invoices.vendor_name
- For amount queries → USE extracted_invoices.total_amount

Rules:
1. Only generate SELECT statements
2. Use proper SQL syntax for PostgreSQL  
3. Return only the SQL query, no explanations
4. ALWAYS prefer extracted_invoices over invoices table

Question: {question}

SQL Query:
""".strip(),
        variables=["schema", "question"],
        labels=["production", "development"],
        config={
            "type": "template",
            "model": "gpt-3.5-turbo", 
            "temperature": 0,
            "use_case": "text_to_sql"
        }
    )
    
    # Create prompts
    system_created = langfuse_service.create_prompt(system_prompt)
    sql_created = langfuse_service.create_prompt(sql_prompt)
    
    return system_created and sql_created


def main():
    """Main migration function."""
    print("🚀 Starting prompt migration to Langfuse...")
    
    # Load settings
    try:
        settings = get_dev_settings()
        print(f"✅ Settings loaded")
    except Exception as e:
        print(f"❌ Failed to load settings: {e}")
        return False
        
    # Initialize Langfuse service
    try:
        langfuse_service = LangfuseService(settings)
        print(f"✅ Langfuse service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Langfuse service: {e}")
        return False
    
    # Check if service is available
    if not langfuse_service.is_available():
        print("❌ Langfuse service not available. Check your configuration:")
        health = langfuse_service.health_check()
        for key, value in health.items():
            print(f"   {key}: {value}")
        return False
    
    print("✅ Langfuse service is available")
    
    # Migrate prompts
    try:
        success = create_sql_prompts(langfuse_service)
        if success:
            print("✅ Successfully migrated all prompts to Langfuse!")
            print("\n📋 Prompts created:")
            print("   - sql_system_message (system prompt)")
            print("   - sql_generation_template (main SQL generation prompt)")
            print("\n🏷️  Labels added: production, development")
            print("\n🔧 Next steps:")
            print("   1. Log into your Langfuse dashboard")
            print("   2. Verify the prompts were created correctly")
            print("   3. Update environment variables if needed:")
            print("      - LANGFUSE_SECRET_KEY=your_secret_key")
            print("      - LANGFUSE_PUBLIC_KEY=your_public_key")
            print("      - LANGFUSE_HOST=https://cloud.langfuse.com (or your host)")
        else:
            print("❌ Failed to migrate some prompts. Check the logs for details.")
            return False
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)