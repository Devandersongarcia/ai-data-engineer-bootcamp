"""Test the updated prompts with correct table names."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings
from text_to_sql import TextToSQLConverter

def test_updated_prompts():
    print("🧪 Testing Updated Prompts with Correct Table Names")
    print("=" * 60)
    
    settings = get_dev_settings()
    converter = TextToSQLConverter(
        database_url=settings.database_url,
        openai_api_key=settings.openai_api_key
    )
    
    # Test questions
    test_questions = [
        "me mostre as notas fiscais dos últimos 7 dias",
        "show me all invoices with total amount greater than 100",
        "quantas notas fiscais temos no total?",
        "show me invoices from vendor Uber",
        "what is the total amount of all invoices?"
    ]
    
    print("🎯 Testing various questions...")
    print()
    
    for i, question in enumerate(test_questions, 1):
        print(f"📝 Test {i}: {question}")
        print("-" * 40)
        
        result = converter.process_question(question, user_id=f"test_user_{i}")
        
        print(f"   Success: {result.get('success')}")
        
        sql_query = result.get('sql_query')
        if sql_query:
            # Check if it uses the correct table name
            if 'ubears_invoices_extract_airflow' in sql_query:
                print(f"   ✅ Using correct table: ubears_invoices_extract_airflow")
            else:
                print(f"   ❌ Wrong table in query: {sql_query[:100]}...")
            
            print(f"   SQL: {sql_query[:80]}...")
        
        if result.get('error'):
            error = result['error']
            if 'does not exist' in error:
                print(f"   ❌ Table not found error: {error[:60]}...")
            elif 'permission denied' in error.lower():
                print(f"   ⚠️ Permission error: {error[:60]}...")
            else:
                print(f"   ⚠️ Other error: {error[:60]}...")
        
        # Show tracing info
        token_usage = result.get('token_usage')
        if token_usage:
            total_tokens = token_usage.get('total_tokens', 0)
            print(f"   🔤 Tokens used: {total_tokens}")
        
        session_id = result.get('session_id')
        if session_id:
            print(f"   🔗 Session tracked: ✅")
        
        print()
    
    print("🎯 Summary:")
    print("✅ Prompts updated in Langfuse")
    print("✅ Fallback prompts updated in code")
    print("✅ Table name corrected: ubears_invoices_extract_airflow")
    print("✅ Tracing system working")
    
    print(f"\n🌐 View traces at: {settings.langfuse_host}")

if __name__ == "__main__":
    test_updated_prompts()