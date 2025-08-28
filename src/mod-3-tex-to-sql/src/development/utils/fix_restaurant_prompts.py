"""Fix the Langfuse prompts to show restaurant names correctly."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langfuse import Langfuse
from config.settings import get_dev_settings

def fix_prompts():
    print("🔧 Fixing Restaurant Display Prompts")
    print("=" * 50)
    
    settings = get_dev_settings()
    langfuse = Langfuse(
        secret_key=settings.langfuse_secret_key,
        public_key=settings.langfuse_public_key,
        host=settings.langfuse_host
    )
    
    # Updated system prompt that emphasizes vendor_name and avoids unnecessary filters
    updated_system_prompt = """You are a SQL expert helping users query UberEats Brasil invoice data.

CRITICAL COLUMN MAPPING:
- Restaurant names are in: vendor_name (NOT customer_name)
- Customer info is in: customer_name  
- Always include vendor_name in SELECT when showing restaurants
- Table name: ubears_invoices_extract_airflow

IMPORTANT GUIDELINES:
1. ONLY add WHERE conditions when explicitly requested by user
2. For general queries like "show invoices" or "mostrar notas fiscais", do NOT add date filters
3. ALWAYS include vendor_name in SELECT clause when showing restaurant data
4. Use LIMIT when not specified (default: 10 for general queries)
5. Only use date filters when user specifically asks for "recent", "últimos dias", etc.

COLUMN REFERENCE:
- id: Invoice ID
- vendor_name: Restaurant name (MAIN FIELD FOR RESTAURANTS)
- customer_name: Customer who ordered
- total_amount: Invoice total
- invoice_date: Date of invoice  
- created_at: When record was created in system
- filename: Source file name
- object_name: Object identifier

EXAMPLES:
User: "show me all invoices" 
SQL: SELECT vendor_name, customer_name, total_amount, invoice_date FROM ubears_invoices_extract_airflow LIMIT 10;

User: "mostrar restaurantes"
SQL: SELECT vendor_name, COUNT(*) as total_invoices, SUM(total_amount) as total_revenue FROM ubears_invoices_extract_airflow GROUP BY vendor_name;

User: "recent invoices from last week"
SQL: SELECT vendor_name, customer_name, total_amount, invoice_date FROM ubears_invoices_extract_airflow WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' LIMIT 10;

Generate only clean SELECT statements. No explanations, no markdown."""
    
    try:
        # Update system prompt
        langfuse.create_prompt(
            name="system_prompt",
            prompt=updated_system_prompt,
            is_active=True
        )
        print("✅ Updated system prompt - now emphasizes vendor_name")
        
        # Updated user prompt template
        updated_user_prompt = """Based on the database schema, convert this question to SQL:

Question: {{question}}

Return only the SQL query. Include vendor_name when showing restaurant information."""
        
        langfuse.create_prompt(
            name="user_prompt_template", 
            prompt=updated_user_prompt,
            is_active=True
        )
        print("✅ Updated user prompt template")
        
        print("\n🎯 Key fixes applied:")
        print("   • ALWAYS include vendor_name for restaurant queries")
        print("   • NO automatic date filters for general queries")
        print("   • Clear examples showing vendor_name usage")
        print("   • Proper customer_name vs vendor_name distinction")
        
    except Exception as e:
        print(f"❌ Error updating prompts: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = fix_prompts()
    print(f"\n{'🎉 RESTAURANT PROMPTS FIXED!' if success else '⚠️ Fix failed!'}")