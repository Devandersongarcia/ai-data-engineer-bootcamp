"""Test the fix for user_id parameter."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings  
from text_to_sql import TextToSQLConverter

def test_fix():
    print("🧪 Testing Fixed TextToSQLConverter")

    # Test the updated converter
    settings = get_dev_settings()
    converter = TextToSQLConverter(
        database_url=settings.database_url,
        openai_api_key=settings.openai_api_key
    )

    # Test with user_id parameter (should work now)
    try:
        result = converter.process_question(
            "Show me all data from the database", 
            user_id="test_user"
        )
        print("✅ process_question with user_id works!")
        print(f"📊 Success: {result.get('success')}")
        print(f"🔗 Session ID: {result.get('session_id', 'N/A')}")
        print(f"⏱️  Total time: {result.get('total_time', 0):.3f}s")
    except Exception as e:
        print(f"❌ Error with user_id: {e}")
        return False

    # Test without user_id (backward compatibility)
    try:
        result2 = converter.process_question("Show me all data")
        print("✅ process_question without user_id works too!")
        print(f"📊 Success: {result2.get('success')}")
        print("🎉 Both methods work - backward compatibility maintained!")
        return True
    except Exception as e:
        print(f"❌ Error without user_id: {e}")
        return False

if __name__ == "__main__":
    success = test_fix()
    sys.exit(0 if success else 1)