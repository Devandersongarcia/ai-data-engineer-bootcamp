# 📋 Scripts Cleanup Analysis

## ✅ KEEP - Current Working Scripts

### Core Production Scripts (KEEP)
- `run_agents.py` ✅ - Simple agent demo (NEW, WORKING)
- `run_production_agents.py` ✅ - Production streaming with agents (NEW, WORKING)
- `run_enhanced_fraud_detection_simple.py` ✅ - Enhanced agent system (NEW, WORKING)
- `test_agents_quick.py` ✅ - Quick agent tests (NEW, WORKING)
- `run_simple_fraud_detection.py` ✅ - Basic Spark fraud detection (WORKING)
- `run_dashboard.py` ✅ - Dashboard launcher (WORKING)

### Utility Scripts (KEEP)
- `check_kafka_topics.py` ✅ - Kafka diagnostics
- `debug_kafka.py` ✅ - Kafka debugging  
- `diagnose_streaming.py` ✅ - Streaming diagnostics
- `setup_spark_env.sh` ✅ - Spark environment setup
- `setup_spark_jars.py` ✅ - JAR file management
- `test_qdrant_integration.py` ✅ - Qdrant testing
- `README_agents.md` ✅ - Documentation

### Legacy Infrastructure (KEEP - but could consolidate)
- `1_start_rag.py` - RAG system startup
- `2_start_kafka.sh` - Kafka startup
- `3_start_spark.py` - Spark startup  
- `4_start_agno.py` - Agent startup
- `start_dev.sh`, `stop_dev.sh` - Dev environment
- `deploy.sh`, `setup.sh` - Deployment
- `init-db.sql` - Database setup

## ❌ REMOVE - Broken/Obsolete Scripts

### Scripts with Missing Dependencies
1. **`run_enhanced_fraud_detection.py`** ❌
   - Imports: `RAGEnhancedFraudProcessor` (DOESN'T EXIST)
   - Imports: `performance_monitor` (DOESN'T EXIST)
   - Status: BROKEN - missing modules
   - Replacement: `run_enhanced_fraud_detection_simple.py`

2. **`run_streaming_production.py`** ❌ 
   - Imports: `RAGEnhancedFraudProcessor` (DOESN'T EXIST)
   - Status: BROKEN - missing modules
   - Replacement: `run_production_agents.py`

3. **`run_streaming_demo.py`** ❌
   - Likely imports: `RAGEnhancedFraudProcessor` (DOESN'T EXIST)
   - Status: PROBABLY BROKEN
   - Replacement: `run_agents.py` for demos

### Potentially Obsolete Scripts
4. **`run_fast_streaming.py`** ⚠️
   - May have outdated imports or functionality
   - Need to verify if still needed

5. **`run_optimized_streaming.py`** ⚠️ 
   - May overlap with newer optimized versions
   - Need to verify relevance

6. **`run_working_streaming.py`** ⚠️
   - Vague name suggests temporary/test version
   - Likely obsolete

7. **`run_confluent_streaming.py`** ⚠️
   - May be superseded by newer streaming scripts
   - Check if still needed

8. **`check_topics.py`** ⚠️
   - Possible duplicate of `check_kafka_topics.py`
   - Verify if redundant

### Old Test/Debug Scripts  
9. **`debug_data_flow.py`** ⚠️
   - May be outdated debugging script
   - Verify if current

10. **`test_manual_flow.py`** ⚠️
    - May be obsolete test script
    - Check if still relevant

11. **`run_final_test.sh`** ⚠️
    - Name suggests one-time test
    - Likely obsolete

12. **`setup_enhanced_system.sh`** ⚠️
    - May be obsolete if enhanced system changed
    - Verify current relevance

## 🎯 Recommended Action Plan

### Phase 1: Remove Definitely Broken (SAFE)
```bash
rm scripts/run_enhanced_fraud_detection.py
rm scripts/run_streaming_production.py  
rm scripts/run_streaming_demo.py
```

### Phase 2: Investigate & Remove Obsolete (VERIFY FIRST)
Test these scripts and remove if broken/obsolete:
- `run_fast_streaming.py`
- `run_optimized_streaming.py` 
- `run_working_streaming.py`
- `run_confluent_streaming.py`
- `check_topics.py` (if duplicate)
- `debug_data_flow.py`
- `test_manual_flow.py`
- `run_final_test.sh`
- `setup_enhanced_system.sh`

### Current Working System
Your fraud detection now uses these WORKING scripts:
- **Agent Demo**: `python scripts/run_agents.py`
- **Production**: `python scripts/run_production_agents.py`  
- **Testing**: `python scripts/test_agents_quick.py`
- **Dashboard**: `python scripts/run_dashboard.py`
- **Simple Fraud**: `python scripts/run_simple_fraud_detection.py`