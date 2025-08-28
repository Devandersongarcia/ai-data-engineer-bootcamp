"""Test script to verify Langfuse integration works correctly."""

import os
import sys
from dotenv import load_dotenv

# Add the parent directories to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings
from core.langfuse_service import LangfuseService, get_fallback_prompt
from core.text_to_sql import TextToSQLConverter

# Load environment variables
load_dotenv()


def test_langfuse_service():
    """Test Langfuse service functionality."""
    print("🧪 Testing Langfuse Service...")
    
    settings = get_dev_settings()
    langfuse_service = LangfuseService(settings)
    
    # Health check
    health = langfuse_service.health_check()
    print("\n📊 Langfuse Health Check:")
    for key, value in health.items():
        status = "✅" if value in [True, "success"] else "❌" if value in [False] else "⚠️"
        print(f"   {status} {key}: {value}")
    
    # Test prompt fetching
    print("\n🔍 Testing Prompt Fetching:")
    
    # Test system message
    system_prompt = langfuse_service.get_prompt("sql_system_message", label="production")
    if system_prompt:
        print("   ✅ System message fetched from Langfuse")
        print(f"      Content preview: {system_prompt[:50]}...")
    else:
        print("   ❌ Failed to fetch system message from Langfuse")
        fallback = get_fallback_prompt("sql_system_message")
        print(f"   ✅ Using fallback: {fallback[:50]}...")
    
    # Test SQL generation template
    sql_prompt = langfuse_service.get_prompt(
        "sql_generation_template",
        variables={"schema": "test_schema", "question": "test_question"},
        label="production"
    )
    if sql_prompt:
        print("   ✅ SQL generation template fetched from Langfuse")
        print(f"      Content preview: {sql_prompt[:100]}...")
    else:
        print("   ❌ Failed to fetch SQL template from Langfuse")
        fallback = get_fallback_prompt(
            "sql_generation_template",
            variables={"schema": "test_schema", "question": "test_question"}
        )
        if fallback:
            print(f"   ✅ Using fallback: {fallback[:100]}...")
        else:
            print("   ❌ Fallback also failed")
    
    return langfuse_service.is_available()


def test_text_to_sql_integration():
    """Test TextToSQLConverter with Langfuse integration."""
    print("\n🧪 Testing TextToSQLConverter Integration...")
    
    try:
        settings = get_dev_settings()
        
        # Test core version
        print("\n🔧 Testing core version...")
        converter_core = TextToSQLConverter(settings, settings.openai_api_key)
        print("   ✅ Core TextToSQLConverter initialized")
        
        # Test root version for backward compatibility
        print("\n🔧 Testing root version (backward compatibility)...")
        from text_to_sql import TextToSQLConverter as TextToSQLConverterRoot
        converter_root = TextToSQLConverterRoot(
            database_url=settings.database_url,
            openai_api_key=settings.openai_api_key
        )
        print("   ✅ Root TextToSQLConverter initialized")
        
        # Test prompt creation without actually calling LLM
        print("\n🔍 Testing prompt creation...")
        
        test_question = "Show me all invoices from the last 7 days"
        
        # Test core version
        prompt_core = converter_core._create_sql_prompt(test_question)
        if prompt_core:
            print("   ✅ Core prompt creation successful")
            print(f"      Prompt preview: {prompt_core[:100]}...")
        else:
            print("   ❌ Core prompt creation failed")
        
        # Test root version
        prompt_root = converter_root._create_sql_prompt(test_question)
        if prompt_root:
            print("   ✅ Root prompt creation successful")
            print(f"      Prompt preview: {prompt_root[:100]}...")
        else:
            print("   ❌ Root prompt creation failed")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error during TextToSQLConverter testing: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 Starting Langfuse Integration Tests...\n")
    
    # Test individual components
    langfuse_ok = test_langfuse_service()
    integration_ok = test_text_to_sql_integration()
    
    # Summary
    print("\n📋 Test Summary:")
    print(f"   Langfuse Service: {'✅ OK' if langfuse_ok else '❌ Failed'}")
    print(f"   TextToSQL Integration: {'✅ OK' if integration_ok else '❌ Failed'}")
    
    if langfuse_ok and integration_ok:
        print("\n🎉 All tests passed! Langfuse integration is working correctly.")
        print("\n📝 Next Steps:")
        print("   1. Set up your Langfuse account at https://cloud.langfuse.com")
        print("   2. Get your API keys and update your .env file:")
        print("      LANGFUSE_SECRET_KEY=sk-lf-...")
        print("      LANGFUSE_PUBLIC_KEY=pk-lf-...")
        print("   3. Run the migration script to create prompts:")
        print("      python src/development/utils/migrate_prompts.py")
        print("   4. Your application will automatically use Langfuse prompts!")
        return True
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")
        print("   The application will fall back to hardcoded prompts if Langfuse is unavailable.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)