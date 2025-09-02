#!/usr/bin/env python3
"""
Step 1: Initialize RAG Knowledge Base
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "rag"))

def main():
    print("🧠 Initializing RAG Knowledge Base...")
    
    try:
        from rag_system.fraud_rag import FraudRAGSystem
        
        # Initialize RAG system
        rag_system = FraudRAGSystem()
        print("✅ RAG system initialized successfully")
        
        # Test knowledge base
        test_query = "What are common fraud patterns?"
        result = rag_system.query(test_query, max_results=3)
        print(f"📚 Knowledge base test: {len(result)} results found")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)