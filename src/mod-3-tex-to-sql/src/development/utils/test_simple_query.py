"""Simple test to isolate the validation issue."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings
from text_to_sql import TextToSQLConverter

def test_simple_query():
    print("🔍 Testing Simple Query Validation")
    print("=" * 40)
    
    settings = get_dev_settings()
    converter = TextToSQLConverter(
        database_url=settings.database_url,
        openai_api_key=settings.openai_api_key
    )
    
    # Test the validation directly
    test_sql = "SELECT * FROM ubears_invoices_extract_airflow LIMIT 5;"
    
    print(f"Testing SQL: {test_sql}")
    
    # Test validation method directly
    is_valid = converter._validate_select_only(test_sql)
    print(f"Validation result: {is_valid}")
    
    if is_valid:
        print("✅ Validation passed")
        
        # Test execution directly
        try:
            result = converter.execute_query(test_sql)
            print(f"Execution result: {result.get('success')}")
            if result.get('error'):
                print(f"Error: {result['error']}")
            if result.get('result') is not None:
                print(f"Rows returned: {len(result['result'])}")
        except Exception as e:
            print(f"Execution error: {e}")
    else:
        print("❌ Validation failed")

if __name__ == "__main__":
    test_simple_query()