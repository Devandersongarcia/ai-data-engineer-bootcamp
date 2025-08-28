#!/usr/bin/env python3
"""
Reset and rebuild Vanna training database
This will clear all training data and rebuild it properly
"""

import os
import shutil
import sys

sys.path.append('.')

def reset_vanna_training():
    """Reset Vanna training database"""
    
    print("🔄 Resetting Vanna.ai training database...")
    
    # ChromaDB storage paths (common locations)
    chroma_paths = [
        "./chroma_db",
        "./vanna_chroma",
        "~/.vanna",
        "./ubereats_brasil_production"
    ]
    
    # Remove ChromaDB storage directories
    for path in chroma_paths:
        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path):
            try:
                shutil.rmtree(expanded_path)
                print(f"✅ Removed: {expanded_path}")
            except Exception as e:
                print(f"❌ Could not remove {expanded_path}: {e}")
        else:
            print(f"⏭️  Not found: {expanded_path}")
    
    print("\n🎓 Now let's rebuild with essential training examples...")
    
    # Essential training examples
    training_examples = [
        {
            "question": "me mostre os pedidos", 
            "sql": "SELECT * FROM orders ORDER BY order_date DESC LIMIT 50"
        },
        {
            "question": "mostre pedidos de hoje",
            "sql": "SELECT * FROM orders WHERE DATE(order_date) = CURRENT_DATE ORDER BY order_date DESC"
        },
        {
            "question": "quantos pedidos temos",
            "sql": "SELECT COUNT(*) as total_pedidos FROM orders"
        },
        {
            "question": "faturamento por método de pagamento", 
            "sql": "SELECT payment_method, COUNT(*) as total_transacoes, SUM(total_amount) as faturamento_total FROM extracted_invoices GROUP BY payment_method ORDER BY faturamento_total DESC"
        },
        {
            "question": "top 10 restaurantes",
            "sql": "SELECT vendor_name, COUNT(*) as total_pedidos FROM extracted_invoices GROUP BY vendor_name ORDER BY total_pedidos DESC LIMIT 10"
        }
    ]
    
    try:
        from core.vanna_converter import VannaTextToSQLConverter
        
        print("🔧 Initializing fresh Vanna converter...")
        converter = VannaTextToSQLConverter(
            database_url=os.getenv('DATABASE_URL', 'postgresql://postgres:123456@localhost:5432/postgres'),
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        print("✅ Converter initialized")
        
        # Add training examples
        print(f"\n📚 Adding {len(training_examples)} training examples...")
        
        for i, example in enumerate(training_examples, 1):
            try:
                result = converter.train_model(example["question"], example["sql"])
                
                if result["success"]:
                    print(f"  ✅ {i}. \"{example['question']}\" → trained successfully")
                else:
                    print(f"  ❌ {i}. \"{example['question']}\" → failed: {result['error']}")
                    
            except Exception as e:
                print(f"  ❌ {i}. \"{example['question']}\" → error: {e}")
        
        print(f"\n🧪 Testing retrieval...")
        
        # Test retrieval
        test_question = "me mostre os pedidos"
        result = converter.convert_to_sql(test_question)
        
        if result["success"]:
            print(f"✅ Test successful! Generated: {result['sql_query'][:50]}...")
        else:
            print(f"❌ Test failed: {result['error']}")
        
        print(f"\n🎉 Training database reset complete!")
        print(f"📋 Next steps:")
        print(f"  1. Restart your Streamlit app")
        print(f"  2. Test the question: '{test_question}'")
        print(f"  3. Add more training examples as needed")
        
    except Exception as e:
        print(f"❌ Failed to rebuild training: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reset_vanna_training()