"""Test with real data to see what's happening with the queries."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings
from text_to_sql import TextToSQLConverter

def test_real_data():
    print("🔍 Testing Real Data Queries")
    print("=" * 40)
    
    settings = get_dev_settings()
    converter = TextToSQLConverter(
        database_url=settings.database_url,
        openai_api_key=settings.openai_api_key
    )
    
    # Test different types of queries
    test_queries = [
        ("Simple select all", "show me all invoices"),
        ("Limit query", "show me 5 invoices"),
        ("Vendor query", "show me invoices from restaurants"),
        ("Amount query", "show me invoices with amounts"),
        ("Date query", "show me recent invoices"),
        ("Portuguese", "me mostre todas as notas fiscais")
    ]
    
    for description, question in test_queries:
        print(f"\n📝 {description}: '{question}'")
        print("-" * 50)
        
        result = converter.process_question(question, user_id="data_test")
        
        if result.get('success'):
            row_count = result.get('row_count', 0)
            sql_query = result.get('sql_query', '')
            
            print(f"   ✅ Success: {row_count} rows returned")
            print(f"   📊 SQL: {sql_query[:80]}...")
            
            # Check if we got actual data
            if row_count > 0:
                print("   🎉 Data found!")
                
                # Show token usage
                token_usage = result.get('token_usage', {})
                if token_usage:
                    print(f"   🔤 Tokens: {token_usage.get('total_tokens', 0)}")
                
                break  # Found working query
            else:
                print("   ⚠️ No rows returned")
                
        else:
            error = result.get('error', '')
            print(f"   ❌ Failed: {error[:60]}...")
    
    # Test a direct simple query
    print(f"\n🎯 Testing Direct Simple Query")
    print("-" * 30)
    
    # Test execution directly
    simple_sql = "SELECT vendor_name, total_amount FROM ubears_invoices_extract_airflow LIMIT 5"
    
    try:
        exec_result = converter.execute_query(simple_sql)
        if exec_result.get('success'):
            row_count = exec_result.get('row_count', 0)
            print(f"   ✅ Direct query works: {row_count} rows")
            
            # Show actual data
            df = exec_result.get('result')
            if df is not None and not df.empty:
                print("   🍔 Sample restaurant data:")
                for idx, row in df.iterrows():
                    vendor = row.get('vendor_name', 'N/A')
                    amount = row.get('total_amount', 0)
                    print(f"      • {vendor}: ${amount}")
            
        else:
            print(f"   ❌ Direct query failed: {exec_result.get('error', '')}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_real_data()