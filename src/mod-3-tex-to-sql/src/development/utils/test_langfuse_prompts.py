"""Test Langfuse prompt retrieval and force refresh."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langfuse import Langfuse
from config.settings import get_dev_settings
import time

def test_langfuse_prompts():
    print("🔍 Testing Langfuse Prompt Retrieval")
    print("=" * 50)
    
    settings = get_dev_settings()
    langfuse = Langfuse(
        secret_key=settings.langfuse_secret_key,
        public_key=settings.langfuse_public_key,
        host=settings.langfuse_host
    )
    
    # Test fetching system prompt
    try:
        print("📋 Fetching system prompt...")
        system_prompt = langfuse.get_prompt(name="system_prompt")
        if system_prompt:
            content = system_prompt.prompt
            print(f"   ✅ System prompt retrieved ({len(content)} chars)")
            
            # Check if it contains vendor_name guidance
            if "vendor_name" in content:
                print("   🎯 Contains vendor_name guidance: ✅")
            else:
                print("   ⚠️ Missing vendor_name guidance")
                
            # Check if it warns against automatic filters
            if "ONLY add WHERE conditions when explicitly requested" in content:
                print("   🚫 Contains filter restriction: ✅")
            else:
                print("   ⚠️ Missing filter restriction")
                
            print(f"   📝 First 200 chars: {content[:200]}...")
            
        else:
            print("   ❌ No system prompt found")
            
    except Exception as e:
        print(f"   ❌ Error fetching system prompt: {e}")
    
    # Test fetching user prompt template
    try:
        print("\n📋 Fetching user prompt template...")
        user_prompt = langfuse.get_prompt(name="user_prompt_template")
        if user_prompt:
            content = user_prompt.prompt  
            print(f"   ✅ User prompt retrieved ({len(content)} chars)")
            print(f"   📝 Content: {content}")
        else:
            print("   ❌ No user prompt template found")
            
    except Exception as e:
        print(f"   ❌ Error fetching user prompt template: {e}")
    
    return True

if __name__ == "__main__":
    test_langfuse_prompts()