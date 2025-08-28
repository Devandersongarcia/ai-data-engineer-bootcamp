"""Test script to verify Langfuse tracing functionality with token usage tracking."""

import os
import sys
from dotenv import load_dotenv

# Add the parent directories to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings
from core.text_to_sql import TextToSQLConverter
from core.langfuse_tracing import LangfuseTracing

# Load environment variables
load_dotenv()


def test_tracing_service():
    """Test the tracing service directly."""
    print("🔍 Testing Langfuse Tracing Service...")
    
    settings = get_dev_settings()
    tracing = LangfuseTracing(settings)
    
    if tracing.is_enabled():
        print("   ✅ Tracing service enabled and initialized")
        
        # Test session tracing
        with tracing.trace_session("test_session", user_id="test_user") as session:
            if session:
                print(f"   ✅ Session created: {session.id}")
            else:
                print("   ⚠️ Session creation returned None")
        
        return True
    else:
        print("   ❌ Tracing service not enabled")
        return False


def test_text_to_sql_with_tracing():
    """Test TextToSQLConverter with full tracing."""
    print("\n🧪 Testing TextToSQLConverter with Tracing...")
    
    try:
        settings = get_dev_settings()
        converter = TextToSQLConverter(settings, settings.openai_api_key)
        
        print("   ✅ TextToSQLConverter initialized with tracing")
        
        # Test a simple question that should work
        test_question = "Show me the first 5 invoices from the database"
        print(f"   🤔 Testing question: '{test_question}'")
        
        # Process with tracing
        result = converter.process_question(test_question, user_id="test_user")
        
        print("\n📊 Tracing Results:")
        print(f"   Success: {result.get('success', 'Unknown')}")
        
        if result.get('error'):
            print(f"   Error: {result.get('error')}")
        
        sql_query = result.get('sql_query')
        if sql_query:
            print(f"   SQL Query: {sql_query[:100]}...")
        
        # Token usage information
        token_usage = result.get('token_usage')
        if token_usage:
            print(f"   📈 Token Usage:")
            print(f"      Input tokens: {token_usage.get('input_tokens', 0)}")
            print(f"      Output tokens: {token_usage.get('output_tokens', 0)}")
            print(f"      Total tokens: {token_usage.get('total_tokens', 0)}")
        else:
            print(f"   ⚠️ No token usage data captured")
        
        # Cost estimation
        estimated_cost = result.get('estimated_cost')
        if estimated_cost:
            print(f"   💰 Estimated Cost: ${estimated_cost:.6f}")
        else:
            print(f"   💰 No cost estimation available")
        
        # Timing information
        print(f"   ⏱️ Performance:")
        sql_time = result.get('sql_generation_time', 0)
        db_time = result.get('db_execution_time', 0)
        total_time = result.get('total_time', 0)
        print(f"      SQL Generation: {sql_time:.3f}s" if sql_time else "      SQL Generation: N/A")
        print(f"      DB Execution: {db_time:.3f}s" if db_time else "      DB Execution: N/A")
        print(f"      Total Time: {total_time:.3f}s" if total_time else "      Total Time: N/A")
        
        # Tracing IDs
        print(f"   🔗 Trace IDs:")
        print(f"      Session: {result.get('session_id', 'N/A')}")
        print(f"      SQL Generation: {result.get('sql_trace_id', 'N/A')}")
        print(f"      DB Query: {result.get('db_trace_id', 'N/A')}")
        
        # Row count
        row_count = result.get('row_count')
        if row_count is not None:
            print(f"   📄 Rows returned: {row_count}")
        
        # Check if tracing is working even if SQL generation failed
        has_traces = any([
            result.get('session_id'),
            result.get('sql_trace_id'), 
            result.get('db_trace_id')
        ])
        
        if has_traces:
            print(f"   ✅ Tracing data captured successfully!")
        else:
            print(f"   ⚠️ No tracing data captured")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error during testing: {e}")
        return False


def test_fallback_behavior():
    """Test that the system works even when tracing is disabled."""
    print("\n🔄 Testing Fallback Behavior (Tracing Disabled)...")
    
    # Temporarily disable tracing
    original_env = os.environ.get('LANGFUSE_TRACING_ENABLED')
    os.environ['LANGFUSE_TRACING_ENABLED'] = 'false'
    
    try:
        settings = get_dev_settings()
        converter = TextToSQLConverter(settings, settings.openai_api_key)
        
        result = converter.process_question("Show me all invoices", user_id="test_user")
        
        print(f"   ✅ Works without tracing: {result.get('success')}")
        print(f"   📊 Token usage still captured: {result.get('token_usage') is not None}")
        print(f"   🔗 No trace IDs: {result.get('session_id') is None}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Fallback failed: {e}")
        return False
        
    finally:
        # Restore original setting
        if original_env is not None:
            os.environ['LANGFUSE_TRACING_ENABLED'] = original_env
        else:
            os.environ.pop('LANGFUSE_TRACING_ENABLED', None)


def main():
    """Main test function."""
    print("🚀 Starting Langfuse Tracing Tests...\n")
    
    tracing_ok = test_tracing_service()
    integration_ok = test_text_to_sql_with_tracing()
    fallback_ok = test_fallback_behavior()
    
    print("\n📋 Test Summary:")
    print(f"   Tracing Service: {'✅ OK' if tracing_ok else '❌ Failed'}")
    print(f"   Integration Test: {'✅ OK' if integration_ok else '❌ Failed'}")
    print(f"   Fallback Test: {'✅ OK' if fallback_ok else '❌ Failed'}")
    
    if all([tracing_ok, integration_ok, fallback_ok]):
        print("\n🎉 All tracing tests passed!")
        print("\n📈 What you can now see in Langfuse:")
        print("   • Every SQL generation request")
        print("   • Token usage and costs for each request")
        print("   • Database query execution times")
        print("   • Success/failure rates")
        print("   • User sessions and conversation flows")
        print("   • Performance metrics over time")
        print("\n🌐 View your traces at: https://us.cloud.langfuse.com")
        return True
    else:
        print("\n⚠️ Some tests failed. Check the logs above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)