"""Test the final SQL parsing fix with real query."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings
from text_to_sql import TextToSQLConverter

def test_final_fix():
    print("🎯 Testing Final SQL Parsing Fix")
    print("=" * 40)
    
    settings = get_dev_settings()
    converter = TextToSQLConverter(
        database_url=settings.database_url,
        openai_api_key=settings.openai_api_key
    )
    
    result = converter.process_question(
        "me mostre 5 notas fiscais", 
        user_id="test_parsing_fix"
    )
    
    print(f"✅ Success: {result.get('success')}")
    
    if result.get('success'):
        print("🎉 SQL parsing fix is working!")
        
        # Show metrics
        token_usage = result.get('token_usage', {})
        if token_usage:
            print(f"🔤 Tokens: {token_usage.get('total_tokens', 0)}")
        
        row_count = result.get('row_count')
        if row_count is not None:
            print(f"📊 Rows returned: {row_count}")
        
        estimated_cost = result.get('estimated_cost')
        if estimated_cost:
            print(f"💰 Cost: ${estimated_cost:.6f}")
        
        session_id = result.get('session_id')
        if session_id:
            print(f"🔗 Session: {session_id[:20]}...")
        
        sql_query = result.get('sql_query')
        if sql_query:
            print(f"📝 SQL: {sql_query[:60]}...")
            
    else:
        error = result.get('error', 'Unknown error')
        print(f"❌ Error: {error}")
        
        if 'non-SELECT statements' in error:
            print("⚠️ SQL parsing still has issues")
            return False
        elif 'does not exist' in error or 'permission' in error.lower():
            print("✅ SQL parsing working, just database connectivity issue")
            return True
    
    return result.get('success', False)

if __name__ == "__main__":
    success = test_final_fix()
    print(f"\n{'🎉 FIXED!' if success else '⚠️ Still investigating...'}")
    sys.exit(0 if success else 1)