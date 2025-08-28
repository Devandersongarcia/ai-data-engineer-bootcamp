"""Update Langfuse prompts with correct table names and schema."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings
from core.langfuse_service import LangfuseService, PromptTemplate

def update_prompts():
    print("🔄 Updating Langfuse prompts with correct table names...")
    print("=" * 60)
    
    settings = get_dev_settings()
    langfuse_service = LangfuseService(settings)
    
    if not langfuse_service.is_available():
        print("❌ Langfuse service not available")
        return False
    
    # Updated SQL generation template with correct table name
    sql_prompt = PromptTemplate(
        name="sql_generation_template", 
        content="""
You are a SQL expert. Convert the following natural language question into a SQL SELECT query.

Database Schema:
{schema}

CRITICAL RULES:
1. ALWAYS use ubears_invoices_extract_airflow table for invoice queries - this is the main table with all data
2. The table has proper DATE/TIMESTAMP fields: invoice_date, due_date, issue_date, created_at, extracted_at, updated_at
3. Use ubears_invoices_extract_airflow.created_at for recent date queries: >= CURRENT_DATE - INTERVAL '7 days'
4. Use ubears_invoices_extract_airflow.invoice_date for invoice-specific date filtering

MANDATORY Table Selection:
- For ANY invoice query → USE ubears_invoices_extract_airflow table
- For date/time queries → USE ubears_invoices_extract_airflow.created_at, invoice_date, or extracted_at
- For vendor/restaurant queries → USE ubears_invoices_extract_airflow.vendor_name
- For amount queries → USE ubears_invoices_extract_airflow.total_amount, subtotal_amount, tax_amount, etc.
- For customer queries → USE ubears_invoices_extract_airflow.customer_name, customer_address, etc.

Available Amount Fields:
- total_amount: Total invoice amount
- subtotal_amount: Amount before tax
- tax_amount: Tax amount
- discount_amount: Discount applied
- shipping_amount: Shipping cost
- amount_paid: Amount already paid
- amount_due: Outstanding amount
- tip_amount: Tip amount

Available Date Fields:
- invoice_date: Date of the invoice
- due_date: Payment due date
- issue_date: Issue date
- created_at: Record creation timestamp
- extracted_at: Data extraction timestamp
- updated_at: Record update timestamp

Rules:
1. Only generate SELECT statements
2. Use proper SQL syntax for PostgreSQL  
3. Return only the SQL query, no explanations
4. ALWAYS use ubears_invoices_extract_airflow as the table name
5. Use appropriate date fields based on the context of the question

Question: {question}

SQL Query:
""".strip(),
        variables=["schema", "question"],
        labels=["production", "development"],
        config={
            "type": "template",
            "model": "gpt-3.5-turbo", 
            "temperature": 0,
            "use_case": "text_to_sql",
            "table_name": "ubears_invoices_extract_airflow"
        }
    )
    
    # Create the updated prompt
    success = langfuse_service.create_prompt(sql_prompt)
    
    if success:
        print("✅ Successfully updated SQL generation prompt!")
        print("🎯 Key changes made:")
        print("   • Table name: extracted_invoices → ubears_invoices_extract_airflow")
        print("   • Added detailed column information")
        print("   • Updated date field references") 
        print("   • Added amount field guidance")
        print("   • Maintained all security rules")
        
        print(f"\n🌐 Updated prompts are now live at: {settings.langfuse_host}")
        return True
    else:
        print("❌ Failed to update prompts")
        return False

if __name__ == "__main__":
    success = update_prompts()
    sys.exit(0 if success else 1)