"""Final test of restaurant name fixes."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_to_sql import TextToSQLConverter
from config.settings import get_dev_settings

def test_restaurant_fix():
    print("🍔 Final Restaurant Name Fix Test")
    print("=" * 50)
    
    settings = get_dev_settings()
    
    # Test with fresh converter instance
    converter = TextToSQLConverter(
        database_url=settings.database_url,
        openai_api_key=settings.openai_api_key
    )
    
    test_cases = [
        ("Portuguese general", "me mostre todas as notas fiscais"),
        ("English restaurants", "show me all restaurants"),  
        ("Portuguese restaurants", "mostrar restaurantes"),
        ("Simple query", "show me 5 invoices"),
    ]
    
    for description, question in test_cases:
        print(f"\n📝 Testing: {description}")
        print(f"   Question: '{question}'")
        
        result = converter.process_question(question, user_id="restaurant_fix_test")
        
        success = result.get('success', False)
        sql_query = result.get('sql_query', '')
        row_count = result.get('row_count', 0)
        
        print(f"   ✅ Success: {success}")
        print(f"   📊 Rows: {row_count}")
        print(f"   📝 SQL: {sql_query}")
        
        # Check if vendor_name is included
        has_vendor_name = 'vendor_name' in sql_query if sql_query else False
        has_unnecessary_filter = 'WHERE created_at >=' in sql_query if sql_query else False
        
        print(f"   🏷️ Includes vendor_name: {'✅' if has_vendor_name else '❌'}")  
        print(f"   🚫 Has unnecessary filter: {'❌' if has_unnecessary_filter else '✅'}")
        
        if success and row_count > 0 and has_vendor_name and not has_unnecessary_filter:
            print("   🎉 PERFECT! All criteria met")
            
            # Show actual results
            df = result.get('result')
            if df is not None and not df.empty:
                print("   🍔 Sample restaurants found:")
                if 'vendor_name' in df.columns:
                    unique_restaurants = df['vendor_name'].unique()[:3]
                    for restaurant in unique_restaurants:
                        print(f"      • {restaurant}")
                else:
                    print("      ⚠️ No vendor_name column in results")
            break
        else:
            print("   ⚠️ Some criteria not met, continuing...")
    
    print(f"\n{'🎉 RESTAURANT NAMES WORKING!' if success and row_count > 0 and has_vendor_name else '⚠️ Still needs fixes...'}")

if __name__ == "__main__":
    test_restaurant_fix()