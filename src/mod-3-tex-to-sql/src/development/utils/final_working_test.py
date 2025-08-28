"""Final working test - use fallback prompts and test directly."""

import sys
import os
os.environ['LANGFUSE_ENABLED'] = 'false'  # Force fallback prompts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_to_sql import TextToSQLConverter
from config.settings import get_dev_settings

def final_working_test():
    print("🎯 Final Working Test - Using Fallback Prompts")
    print("=" * 60)
    
    settings = get_dev_settings()
    converter = TextToSQLConverter(
        database_url=settings.database_url,
        openai_api_key=settings.openai_api_key
    )
    
    print("🚫 Langfuse disabled - using fallback prompts")
    
    # Test cases that should now work with vendor_name
    test_cases = [
        "mostrar todos os restaurantes",
        "show me all restaurants", 
        "me mostre as notas fiscais",
        "show me 5 invoices"
    ]
    
    for question in test_cases:
        print(f"\n📝 Testing: '{question}'")
        
        result = converter.process_question(question, user_id='fallback_test')
        
        sql_query = result.get('sql_query', '')
        success = result.get('success', False)
        row_count = result.get('row_count', 0) if result.get('result') is not None else 0
        
        print(f"   📊 Success: {success}")
        print(f"   📈 Rows: {row_count}")  
        print(f"   📝 SQL: {sql_query}")
        
        # Key checks
        has_vendor_name = 'vendor_name' in sql_query
        has_bad_filter = 'WHERE created_at >=' in sql_query and 'recent' not in question.lower()
        
        print(f"   🏷️ Has vendor_name: {'✅' if has_vendor_name else '❌'}")
        print(f"   🚫 Unnecessary filter: {'❌' if has_bad_filter else '✅'}")
        
        if success and row_count > 0 and has_vendor_name:
            print("   🎉 SUCCESS! Restaurant data retrieved!")
            
            df = result.get('result')
            if df is not None and 'vendor_name' in df.columns:
                restaurants = df['vendor_name'].unique()
                print(f"   🍔 Found {len(restaurants)} restaurants:")
                for restaurant in restaurants[:3]:
                    print(f"      • {restaurant}")
            break
        else:
            print("   ⚠️ Still has issues...")
    
    print(f"\n{'🎉 RESTAURANT NAMES WORKING WITH FALLBACK!' if success and has_vendor_name else '⚠️ Still investigating...'}")
    return success and has_vendor_name

if __name__ == "__main__":
    final_working_test()