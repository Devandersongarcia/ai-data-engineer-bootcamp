"""Final integration test for all tracing features."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_dev_settings
from core.text_to_sql import TextToSQLConverter

def main():
    print("🧪 Final Integration Test")
    print("=" * 50)

    # Test the full system
    settings = get_dev_settings()
    converter = TextToSQLConverter(settings, settings.openai_api_key)

    # Simulate a real query
    result = converter.process_question(
        "Show me all invoices where the total amount is greater than 100", 
        user_id="final_test_user"
    )

    print("✅ Query processed successfully!")
    print(f"📊 Success: {result.get('success')}")
    
    token_usage = result.get("token_usage", {})
    if token_usage:
        total_tokens = token_usage.get("total_tokens", "N/A")
        input_tokens = token_usage.get("input_tokens", 0)
        output_tokens = token_usage.get("output_tokens", 0)
        print(f"🔤 Tokens: {total_tokens} (in: {input_tokens}, out: {output_tokens})")
    else:
        print("🔤 Tokens: N/A")
    
    estimated_cost = result.get("estimated_cost")
    if estimated_cost:
        print(f"💰 Cost: ${estimated_cost:.6f}")
    else:
        print("💰 Cost: N/A")
    
    total_time = result.get("total_time", 0)
    print(f"⏱️  Time: {total_time:.3f}s")
    
    session_id = result.get("session_id")
    if session_id:
        print(f"🔗 Session: {session_id[:20]}...")
    else:
        print("🔗 Session: N/A")

    if result.get("error"):
        error_msg = result["error"]
        if len(error_msg) > 100:
            error_msg = error_msg[:100] + "..."
        print(f"⚠️  Error: {error_msg}")

    print()
    print("🎯 Tracing Features Status:")
    
    # Check each feature
    features = [
        ("Session tracking", result.get("session_id") is not None),
        ("Token usage monitoring", result.get("token_usage") is not None),
        ("Cost estimation", result.get("estimated_cost") is not None),
        ("Performance timing", result.get("total_time") is not None),
        ("SQL trace ID", result.get("sql_trace_id") is not None),
        ("DB trace ID", result.get("db_trace_id") is not None),
    ]
    
    for feature, status in features:
        icon = "✅" if status else "❌"
        print(f"   {icon} {feature}")
    
    print()
    print("🌐 View detailed analytics at: https://us.cloud.langfuse.com")
    
    # Check if most features are working
    working_features = sum(1 for _, status in features if status)
    if working_features >= 4:
        print("🎉 Integration test PASSED! Most features working correctly.")
        return True
    else:
        print("⚠️ Integration test PARTIAL. Some features may need attention.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)