#!/usr/bin/env python3
"""
Test OpenAI Integration for UberEats Delivery Optimization
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openai_connection():
    """Test OpenAI API connection and model availability"""
    
    print("🤖 Testing OpenAI Integration")
    print("=" * 50)
    
    # Check if API key is configured
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False
    
    print(f"✅ API Key configured: {api_key[:10]}...")
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        print("🔄 Testing OpenAI API connection...")
        
        # Test with a simple delivery optimization prompt
        response = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI agent for UberEats delivery optimization. You help optimize routes, predict ETAs, and allocate drivers efficiently."
                },
                {
                    "role": "user", 
                    "content": "A driver in Vila Olimpia, São Paulo is experiencing heavy traffic while delivering to a customer. What optimization recommendations would you suggest?"
                }
            ],
            max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', 1000)),
            temperature=float(os.getenv('OPENAI_TEMPERATURE', 0.7))
        )
        
        print("✅ OpenAI API connection successful!")
        print()
        print("🤖 Sample Agent Response:")
        print("-" * 30)
        print(response.choices[0].message.content)
        print("-" * 30)
        print()
        
        # Test model info
        model_used = response.model
        tokens_used = response.usage.total_tokens
        
        print(f"📊 API Details:")
        print(f"   Model: {model_used}")
        print(f"   Tokens used: {tokens_used}")
        print(f"   Temperature: {os.getenv('OPENAI_TEMPERATURE', 0.7)}")
        print(f"   Max tokens: {os.getenv('OPENAI_MAX_TOKENS', 1000)}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API test failed: {e}")
        return False

def test_delivery_optimization_scenarios():
    """Test OpenAI with specific delivery optimization scenarios"""
    
    print("\n🎯 Testing Delivery Optimization Scenarios")
    print("=" * 50)
    
    api_key = os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)
    
    # Test scenarios based on GPS data patterns
    scenarios = [
        {
            "name": "ETA Prediction",
            "prompt": "Driver moving at 25 km/h in moderate traffic, 2.8km from pickup in Vila_Olimpia business district. Calculate ETA."
        },
        {
            "name": "Route Optimization", 
            "prompt": "Heavy traffic detected in Centro, driver speed dropped to 8 km/h. Suggest route optimization."
        },
        {
            "name": "Driver Allocation",
            "prompt": "Idle driver available in Itaim_Bibi business district. Recommend allocation strategy."
        }
    ]
    
    for scenario in scenarios:
        print(f"\n🔍 Testing: {scenario['name']}")
        print(f"Scenario: {scenario['prompt']}")
        
        try:
            response = client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                messages=[
                    {
                        "role": "system",
                        "content": "You are a UberEats delivery optimization agent. Provide concise, actionable recommendations for delivery efficiency. Focus on time savings, cost reduction, and customer satisfaction."
                    },
                    {
                        "role": "user",
                        "content": scenario['prompt']
                    }
                ],
                max_tokens=200,
                temperature=0.3  # Lower temperature for more consistent optimization
            )
            
            print(f"🤖 Agent Response:")
            print(f"   {response.choices[0].message.content}")
            print(f"   [Tokens: {response.usage.total_tokens}]")
            
        except Exception as e:
            print(f"❌ Scenario test failed: {e}")
    
    print("\n✅ All scenario tests completed!")

def main():
    """Main test function"""
    print("🚚 UberEats OpenAI Integration Test")
    print("Testing delivery optimization with GPT-4o-mini")
    print("=" * 60)
    
    # Test basic connection
    if not test_openai_connection():
        print("❌ Basic connection test failed. Check your API key.")
        return
    
    # Test delivery scenarios
    test_delivery_optimization_scenarios()
    
    print("\n🎉 OpenAI integration is ready for delivery optimization!")
    print("💡 Your agents can now use GPT-4o-mini for real-time decisions")

if __name__ == "__main__":
    main()