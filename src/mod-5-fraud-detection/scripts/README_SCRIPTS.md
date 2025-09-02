# 📁 Scripts Directory - Current Inventory

## 🚀 Main Execution Scripts

### ✅ Production Ready (RECOMMENDED)
- **`run_agents.py`** - Quick agent demo and testing
- **`run_production_agents.py`** - Production streaming with CrewAI agents  
- **`run_enhanced_fraud_detection_simple.py`** - Full agent system with demos
- **`test_agents_quick.py`** - Fast agent system verification
- **`run_simple_fraud_detection.py`** - Basic Spark fraud detection (no agents)

## 🔧 Development & Utilities

### System Management
- **`1_start_rag.py`** - RAG system startup
- **`2_start_kafka.sh`** - Kafka environment startup  
- **`3_start_spark.py`** - Spark environment startup
- **`4_start_agno.py`** - Agent system startup
- **`start_dev.sh`** / **`stop_dev.sh`** - Development environment control

### Diagnostics & Testing
- **`check_kafka_topics.py`** - Kafka topics and connection diagnostics
- **`debug_kafka.py`** - Kafka debugging utilities
- **`diagnose_streaming.py`** - Streaming pipeline diagnostics  
- **`test_qdrant_integration.py`** - Qdrant vector database testing
- **`test_manual_flow.py`** - Manual workflow testing

### Setup & Deployment
- **`setup_spark_env.sh`** - Spark environment configuration
- **`setup_spark_jars.py`** - JAR dependency management
- **`deploy.sh`** - Deployment script
- **`setup.sh`** - General setup script
- **`init-db.sql`** - Database initialization

## ⚠️ Legacy Streaming Scripts (TO REVIEW)

These may have overlapping functionality - consider consolidation:
- **`run_confluent_streaming.py`** - Confluent Cloud specific streaming
- **`run_fast_streaming.py`** - Fast streaming implementation  
- **`run_optimized_streaming.py`** - Optimized streaming version
- **`run_working_streaming.py`** - Working streaming implementation
- **`debug_data_flow.py`** - Data flow debugging
- **`setup_enhanced_system.sh`** - Enhanced system setup

## 📚 Documentation
- **`README_agents.md`** - Agent system documentation
- **`README_SCRIPTS.md`** - This file
- **`CLEANUP_ANALYSIS.md`** - Cleanup analysis and recommendations

## 🎯 Quick Start Commands

### For Agent-Based Fraud Detection:
```bash
# Quick demo
python scripts/run_agents.py

# Production streaming  
python scripts/run_production_agents.py

# Full system test
python scripts/run_enhanced_fraud_detection_simple.py --mode test
```

### For Basic Fraud Detection:
```bash
# Simple Spark-based detection
python scripts/run_simple_fraud_detection.py
```

### For System Diagnostics:
```bash
# Check Kafka connectivity
python scripts/check_kafka_topics.py

# Test Qdrant integration
python scripts/test_qdrant_integration.py

# Quick agent test
python scripts/test_agents_quick.py
```

## 🧹 Cleanup Summary

**Removed (5 broken scripts):**
- ❌ `run_enhanced_fraud_detection.py` - Missing RAGEnhancedFraudProcessor
- ❌ `run_streaming_production.py` - Missing dependencies  
- ❌ `run_streaming_demo.py` - Missing performance_monitor
- ❌ `check_topics.py` - Duplicate of check_kafka_topics.py
- ❌ `run_final_test.sh` - One-time test script

**Current Status:** ✅ 24 scripts remaining (6 production-ready + 18 utilities/legacy)

The scripts folder is now cleaner with broken dependencies removed and working scripts clearly identified.